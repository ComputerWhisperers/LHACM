class LhacmPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._loaded) {
      this._loaded = true;
      this._load();
    }
  }

  connectedCallback() {
    this.attachShadow({ mode: "open" });
    this._repositories = [];
    this._search = "";
    this._group = "status";
    this._sort = "name";
    this._dialog = false;
    this._dialogData = { repository: "", category: "integration" };
    this._render();
  }

  _load() {
    Promise.all([
      this._send({ type: "lhacm/info" }),
      this._send({ type: "lhacm/repositories/list" }),
    ]).then((results) => {
      this._info = results[0];
      this._repositories = results[1];
      this._render();
    }).catch((err) => {
      this._error = err.message || String(err);
      this._render();
    });
  }

  _send(message) {
    return this._hass.connection.sendMessagePromise(message);
  }

  _filteredRepositories() {
    const search = this._search.trim().toLowerCase();
    return (this._repositories || []).slice()
      .filter((repo) => {
        if (!search) return true;
        return [
          repo.name,
          repo.full_name,
          repo.description,
          repo.category,
          repo.status,
          repo.domain,
        ].concat(repo.topics || [])
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(search);
      })
      .sort((a, b) => {
        if (this._sort === "stars") return (b.stars || 0) - (a.stars || 0);
        if (this._sort === "activity") {
          return String(b.last_updated || "").localeCompare(String(a.last_updated || ""));
        }
        if (this._sort === "type") return a.category.localeCompare(b.category);
        return a.name.localeCompare(b.name);
      });
  }

  _groupedRepositories() {
    const groups = new Map();
    for (const repo of this._filteredRepositories()) {
      const key = this._group === "type" ? repo.category : repo.installed ? "downloaded" : "available";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(repo);
    }
    return groups;
  }

  _render() {
    if (!this.shadowRoot) return;
    const groups = this._groupedRepositories();
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          color: var(--primary-text-color, #202124);
          background: var(--primary-background-color, #fff);
          min-height: 100vh;
          font-family: var(--paper-font-body1_-_font-family, Roboto, Arial, sans-serif);
        }
        header {
          height: 64px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 24px;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
          box-sizing: border-box;
        }
        h1 {
          font-size: 20px;
          font-weight: 400;
          margin: 0;
        }
        .toolbar {
          display: grid;
          grid-template-columns: auto minmax(220px, 1fr) auto auto auto;
          gap: 12px;
          align-items: center;
          padding: 12px 16px;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        button, select, input {
          height: 36px;
          border: 1px solid var(--divider-color, #d0d0d0);
          border-radius: 6px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #202124);
          font: inherit;
        }
        button {
          padding: 0 12px;
          cursor: pointer;
        }
        .icon-button {
          width: 40px;
          padding: 0;
          font-size: 22px;
          line-height: 1;
        }
        input {
          padding: 0 14px;
          min-width: 0;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
          font-size: 14px;
        }
        th, td {
          border-bottom: 1px solid var(--divider-color, #e6e6e6);
          padding: 12px 10px;
          text-align: left;
          vertical-align: middle;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        th {
          height: 48px;
          font-weight: 500;
          color: var(--secondary-text-color, #5f6368);
        }
        .group td {
          background: var(--secondary-background-color, #f7f7f7);
          color: var(--primary-text-color, #202124);
          font-weight: 500;
          height: 48px;
        }
        .repo {
          display: flex;
          gap: 12px;
          align-items: center;
          min-width: 0;
        }
        .repo-icon {
          width: 32px;
          height: 32px;
          border-radius: 4px;
          flex: 0 0 auto;
          background: #132238;
          display: grid;
          place-items: center;
          color: #41bdf5;
          font-size: 12px;
          font-weight: 700;
        }
        .repo-text {
          min-width: 0;
        }
        .name {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .description {
          color: var(--secondary-text-color, #5f6368);
          font-size: 13px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          margin-top: 2px;
        }
        .actions {
          text-align: right;
          width: 56px;
        }
        .empty, .error {
          padding: 40px 24px;
          color: var(--secondary-text-color, #5f6368);
        }
        .menu {
          position: absolute;
          top: 54px;
          right: 12px;
          width: 240px;
          background: var(--card-background-color, #fff);
          border: 1px solid var(--divider-color, #ddd);
          box-shadow: 0 4px 12px rgba(0,0,0,.18);
          z-index: 2;
        }
        .menu button {
          width: 100%;
          border: 0;
          border-radius: 0;
          text-align: left;
          height: 50px;
          padding: 0 18px;
        }
        .row-menu-popover {
          position: fixed;
          width: 230px;
          background: var(--card-background-color, #fff);
          border: 1px solid var(--divider-color, #ddd);
          box-shadow: 0 4px 12px rgba(0,0,0,.2);
          z-index: 4;
          padding: 8px 0;
        }
        .row-menu-popover button {
          width: 100%;
          height: 48px;
          border: 0;
          border-radius: 0;
          text-align: left;
          padding: 0 18px;
          background: transparent;
          display: flex;
          align-items: center;
          gap: 18px;
        }
        .row-menu-popover .divider {
          height: 1px;
          background: var(--divider-color, #ddd);
          margin: 8px 0;
        }
        .row-menu-popover .warning {
          color: #f29900;
        }
        .row-menu-popover .danger {
          color: #d93025;
        }
        .row-menu {
          border: 0;
          background: transparent;
          border-radius: 50%;
          color: var(--secondary-text-color, #5f6368);
        }
        .row-menu:hover {
          background: var(--secondary-background-color, #f1f3f4);
        }
        .menu-icon {
          width: 18px;
          height: 18px;
          flex: 0 0 18px;
          color: currentColor;
        }
        .menu-icon svg {
          width: 18px;
          height: 18px;
          display: block;
          fill: currentColor;
        }
        .dialog-backdrop {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,.38);
          display: grid;
          place-items: center;
          z-index: 5;
        }
        .dialog {
          width: min(520px, calc(100vw - 32px));
          max-height: min(680px, calc(100vh - 32px));
          background: var(--card-background-color, #fff);
          border-radius: 24px;
          box-shadow: 0 10px 28px rgba(0,0,0,.25);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .dialog header {
          height: 72px;
          border: 0;
          justify-content: flex-start;
          gap: 12px;
        }
        .dialog h2 {
          font-size: 22px;
          font-weight: 400;
          margin: 0;
        }
        .dialog-body {
          padding: 0 22px 16px;
          overflow: auto;
        }
        .custom-row {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 12px;
          align-items: center;
          padding: 10px 0;
        }
        .custom-row .sub {
          color: var(--secondary-text-color, #5f6368);
          font-size: 13px;
          margin-top: 4px;
        }
        .delete {
          color: #d93025;
          border: 0;
          font-size: 22px;
        }
        .trash-button {
          width: 40px;
          padding: 0;
          font-size: 28px;
          line-height: 1;
        }
        .form {
          display: grid;
          gap: 14px;
          margin-top: 14px;
        }
        .form input, .form select {
          width: 100%;
          box-sizing: border-box;
          height: 48px;
        }
        .dialog-actions {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          padding: 8px 22px 18px;
        }
        .primary {
          color: var(--primary-color, #03a9f4);
          border: 0;
          font-weight: 500;
        }
        @media (max-width: 720px) {
          .toolbar {
            grid-template-columns: 1fr auto;
          }
          .toolbar button:first-child, .toolbar select {
            display: none;
          }
          .wide {
            display: none;
          }
        }
      </style>
      <header>
        <h1>Local Home Assistant Component Manager</h1>
        <button class="icon-button" id="menuButton" title="Menu">&#8942;</button>
        ${this._menu ? `<div class="menu">
          <button id="docsButton">Documentation</button>
          <button id="sourceButton">Repository</button>
          <button id="customButton">Custom repositories</button>
          <button id="aboutButton">About LHACM</button>
        </div>` : ""}
      </header>
      <div class="toolbar">
        <button id="filtersButton">Filters</button>
        <input id="searchInput" placeholder="Search repositories" value="${this._escape(this._search)}">
        <select id="groupSelect" title="Group repositories">
          <option value="status" ${this._group === "status" ? "selected" : ""}>Group by Status</option>
          <option value="type" ${this._group === "type" ? "selected" : ""}>Group by Type</option>
        </select>
        <select id="sortSelect" title="Sort repositories">
          <option value="name" ${this._sort === "name" ? "selected" : ""}>Sort by Name</option>
          <option value="stars" ${this._sort === "stars" ? "selected" : ""}>Sort by Stars</option>
          <option value="activity" ${this._sort === "activity" ? "selected" : ""}>Sort by Activity</option>
          <option value="type" ${this._sort === "type" ? "selected" : ""}>Sort by Type</option>
        </select>
        <button id="refreshButton" title="Refresh">Refresh</button>
      </div>
      ${this._error ? `<div class="error">${this._escape(this._error)}</div>` : this._table(groups)}
      ${this._rowMenu ? this._rowMenuTemplate() : ""}
      ${this._dialog ? this._dialogTemplate() : ""}
    `;
    this._bind();
  }

  _table(groups) {
    if (!groups.size) {
      return `<div class="empty">Use the menu to add GitLab or Gitea custom repositories.</div>`;
    }
    const rows = [];
    rows.push(`<table><thead><tr>
      <th>Repository name</th>
      <th class="wide">Downloads</th>
      <th class="wide">Stars</th>
      <th class="wide">Activity</th>
      <th>Type</th>
      <th class="wide">Installed</th>
      <th class="wide">Latest</th>
      <th class="actions"></th>
    </tr></thead><tbody>`);
    for (const [group, repos] of groups.entries()) {
      rows.push(`<tr class="group"><td colspan="8">^ ${this._groupLabel(group)}</td></tr>`);
      for (const repo of repos) {
        rows.push(`<tr>
          <td><div class="repo"><div class="repo-icon">${this._repoInitials(repo)}</div><div class="repo-text">
            <div class="name">${this._escape(repo.name)}</div>
            <div class="description">${this._escape(repo.description || repo.full_name)}</div>
          </div></div></td>
          <td class="wide">${repo.downloads || "-"}</td>
          <td class="wide">${repo.stars || 0}</td>
          <td class="wide">${this._escape(repo.last_updated || "-")}</td>
          <td>${this._typeLabel(repo.category)}</td>
          <td class="wide">${this._escape(repo.installed_version || "-")}</td>
          <td class="wide">${this._escape(repo.available_version || "-")}</td>
          <td class="actions"><button class="icon-button row-menu" data-id="${this._escape(repo.id)}" title="Repository menu">&#8942;</button></td>
        </tr>`);
      }
    }
    rows.push("</tbody></table>");
    return rows.join("");
  }

  _dialogTemplate() {
    const custom = (this._repositories || []).filter((repo) => repo.custom);
    const categories = this._info && this._info.categories ? this._info.categories : ["integration", "plugin", "theme", "python_script", "appdaemon", "template"];
    return `<div class="dialog-backdrop">
      <div class="dialog">
        <header><button class="icon-button" id="closeDialog">x</button><h2>Custom repositories</h2></header>
        <div class="dialog-body">
          ${custom.map((repo) => `<div class="custom-row">
            <div><div>${this._escape(repo.name)}</div><div class="sub">${this._escape(repo.full_name)} (${this._typeLabel(repo.category)})</div></div>
            <button class="delete trash-button" data-remove="${this._escape(repo.id)}" title="Remove repository" aria-label="Remove repository">&#128465;</button>
          </div>`).join("")}
          <div class="form">
            <input id="repoInput" placeholder="Repository" value="${this._escape(this._dialogData.repository)}">
            <select id="categoryInput">
              ${categories.map((category) => `<option value="${category}" ${this._dialogData.category === category ? "selected" : ""}>${this._typeLabel(category)}</option>`).join("")}
            </select>
            ${this._dialogError ? `<div class="error">${this._escape(this._dialogError)}</div>` : ""}
          </div>
        </div>
        <div class="dialog-actions">
          <button class="primary" id="cancelDialog">CANCEL</button>
          <button class="primary" id="addRepository" ${!this._dialogData.repository ? "disabled" : ""}>ADD</button>
        </div>
      </div>
    </div>`;
  }

  _bind() {
    this._on("menuButton", "click", () => {
      this._menu = !this._menu;
      this._render();
    });
    this._on("customButton", "click", () => {
      this._menu = false;
      this._dialog = true;
      this._render();
    });
    this._on("docsButton", "click", () => window.open("https://github.com/ComputerWhisperers/LHACM", "_blank"));
    this._on("sourceButton", "click", () => window.open("https://github.com/ComputerWhisperers/LHACM", "_blank"));
    this._on("aboutButton", "click", () => alert("LHACM manages Home Assistant custom repositories from GitLab and Gitea."));
    this._on("refreshButton", "click", () => this._refreshRepositories());
    this._on("searchInput", "input", (ev) => {
      this._search = ev.target.value;
      this._render();
    });
    this._on("groupSelect", "change", (ev) => {
      this._group = ev.target.value;
      this._render();
    });
    this._on("sortSelect", "change", (ev) => {
      this._sort = ev.target.value;
      this._render();
    });
    this.shadowRoot.querySelectorAll(".row-menu").forEach((button) => {
      button.addEventListener("click", (ev) => this._openRowMenu(button.dataset.id, ev));
    });
    this.shadowRoot.querySelectorAll("[data-row-action]").forEach((button) => {
      button.addEventListener("click", () => {
        this._repositoryAction(button.dataset.rowAction, button.dataset.id);
      });
    });
    this._on("closeDialog", "click", () => this._closeDialog());
    this._on("cancelDialog", "click", () => this._closeDialog());
    this._on("repoInput", "input", (ev) => {
      this._dialogData.repository = ev.target.value;
      this._render();
    });
    this._on("categoryInput", "change", (ev) => {
      this._dialogData.category = ev.target.value;
    });
    this._on("addRepository", "click", () => this._addRepository());
    this.shadowRoot.querySelectorAll("[data-remove]").forEach((button) => {
      button.addEventListener("click", () => this._removeRepository(button.dataset.remove));
    });
  }

  _on(id, eventName, handler) {
    const element = this.shadowRoot.getElementById(id);
    if (element) {
      element.addEventListener(eventName, handler);
    }
  }

  _addRepository() {
    this._dialogError = "";
    this._send({
        type: "lhacm/repositories/add",
        repository: this._dialogData.repository,
        category: this._dialogData.category,
      }).then(() => {
      this._dialogData.repository = "";
      return this._send({ type: "lhacm/repositories/list" });
    }).then((repositories) => {
      this._repositories = repositories;
      this._render();
    }).catch((err) => {
      this._dialogError = err.message || String(err);
      this._render();
    });
  }

  _removeRepository(id) {
    this._send({ type: "lhacm/repositories/remove", repository: id }).then(() => {
      return this._send({ type: "lhacm/repositories/list" });
    }).then((repositories) => {
      this._repositories = repositories;
      this._render();
    });
  }

  _openRowMenu(id, ev) {
    const rect = ev.target.getBoundingClientRect();
    this._rowMenu = {
      id,
      top: Math.min(rect.bottom + 6, window.innerHeight - 330),
      left: Math.max(8, Math.min(rect.right - 230, window.innerWidth - 238)),
    };
    this._render();
  }

  _rowMenuTemplate() {
    const repo = this._repositories.find((item) => item.id === this._rowMenu.id);
    if (!repo) return "";
    const id = this._escape(repo.id);
    const primaryAction = repo.installed ? "redownload" : "install";
    const primaryLabel = repo.installed
      ? repo.pending_upgrade ? "Update" : "Redownload"
      : "Download";
    return `<div class="row-menu-popover" style="top:${this._rowMenu.top}px;left:${this._rowMenu.left}px">
      <button data-row-action="details" data-id="${id}">${this._menuIcon("info")}<span>Show details</span></button>
      <button data-row-action="repository" data-id="${id}">${this._menuIcon("github")}<span>Repository</span></button>
      <button data-row-action="refresh" data-id="${id}">${this._menuIcon("refresh")}<span>Update information</span></button>
      <button data-row-action="${primaryAction}" data-id="${id}">${this._menuIcon(primaryAction === "install" ? "download" : "redownload")}<span>${primaryLabel}</span></button>
      <div class="divider"></div>
      ${repo.installed ? `<button data-row-action="uninstall" data-id="${id}" class="warning">${this._menuIcon("warning")}<span>Uninstall</span></button>` : ""}
      <button data-row-action="remove" data-id="${id}" class="danger">${this._menuIcon("remove")}<span>Remove</span></button>
    </div>`;
  }

  _menuIcon(name) {
    const paths = {
      info: "M11 17H13V11H11M12 2A10 10 0 1 0 12 22A10 10 0 0 0 12 2M12 20A8 8 0 1 1 12 4A8 8 0 0 1 12 20M11 9H13V7H11",
      github: "M12 2A10 10 0 0 0 2 12C2 16.42 4.87 20.17 8.84 21.5C9.34 21.58 9.5 21.27 9.5 21V19.23C6.73 19.83 6.14 17.89 6.14 17.89C5.68 16.73 5.03 16.42 5.03 16.42C4.12 15.8 5.1 15.82 5.1 15.82C6.1 15.9 6.63 16.85 6.63 16.85C7.5 18.36 8.97 17.92 9.54 17.67C9.63 17.03 9.89 16.59 10.17 16.34C7.95 16.09 5.62 15.23 5.62 11.42C5.62 10.33 6 9.44 6.65 8.75C6.55 8.5 6.2 7.5 6.75 6.12C6.75 6.12 7.59 5.85 9.5 7.15C10.29 6.93 11.15 6.82 12 6.82C12.85 6.82 13.71 6.93 14.5 7.15C16.41 5.85 17.25 6.12 17.25 6.12C17.8 7.5 17.45 8.5 17.35 8.75C18 9.44 18.38 10.33 18.38 11.42C18.38 15.24 16.04 16.09 13.81 16.34C14.17 16.65 14.5 17.26 14.5 18.2V21C14.5 21.27 14.66 21.59 15.17 21.5C19.14 20.16 22 16.42 22 12A10 10 0 0 0 12 2Z",
      refresh: "M17.65 6.35A7.95 7.95 0 0 0 12 4A8 8 0 1 0 19.75 10H17.65A6 6 0 1 1 16.24 7.76L13 11H20V4",
      download: "M5 20H19V18H5M19 9H15V3H9V9H5L12 16",
      redownload: "M12 4V1L8 5L12 9V6A6 6 0 1 1 6 12H4A8 8 0 1 0 12 4M11 10V15H8L12 19L16 15H13V10",
      warning: "M1 21H23L12 2M13 18H11V16H13M13 14H11V10H13",
      remove: "M18.3 5.71L12 12L5.7 5.71L4.29 7.12L10.59 13.41L4.29 19.71L5.7 21.12L12 14.83L18.3 21.12L19.71 19.71L13.41 13.41L19.71 7.12",
    };
    return `<span class="menu-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="${paths[name] || paths.info}"></path></svg></span>`;
  }

  _repositoryAction(action, id) {
    this._rowMenu = undefined;
    if (action === "install" || action === "redownload") {
      this._download(id);
    } else if (action === "uninstall") {
      this._uninstall(id);
    } else if (action === "remove") {
      this._removeRepository(id);
    } else if (action === "refresh") {
      this._refreshOne(id);
    } else if (action === "repository") {
      this._openRepository(id);
    } else if (action === "details") {
      this._showDetails(id);
    }
  }

  _download(id) {
    const repo = this._repositories.find((item) => item.id === id);
    if (!repo) return;
    const message = repo.installed
      ? { type: "lhacm/repository/download", repository: id, version: repo.available_version || undefined }
      : { type: "lhacm/repository/download", repository: id };
    this._send(message).then(() => {
      return this._send({ type: "lhacm/repositories/list" });
    }).then((repositories) => {
      this._repositories = repositories;
      this._render();
    });
  }

  _uninstall(id) {
    this._send({ type: "lhacm/repository/uninstall", repository: id }).then(() => {
      return this._send({ type: "lhacm/repositories/list" });
    }).then((repositories) => {
      this._repositories = repositories;
      this._render();
    });
  }

  _refreshRepositories() {
    this._send({ type: "lhacm/repositories/refresh" }).then((repositories) => {
      this._repositories = repositories;
      this._render();
    }).catch((err) => {
      this._error = err.message || String(err);
      this._render();
    });
  }

  _refreshOne(id) {
    this._send({ type: "lhacm/repository/refresh", repository: id }).then(() => {
      return this._send({ type: "lhacm/repositories/list" });
    }).then((repositories) => {
      this._repositories = repositories;
      this._render();
    });
  }

  _openRepository(id) {
    const repo = this._repositories.find((item) => item.id === id);
    if (repo && repo.source_url) {
      window.open(repo.source_url, "_blank");
    }
    this._render();
  }

  _showDetails(id) {
    const repo = this._repositories.find((item) => item.id === id);
    if (repo) {
      alert(`${repo.name}\n${repo.full_name}\nInstalled: ${repo.installed_version || "-"}\nLatest: ${repo.available_version || "-"}`);
    }
    this._render();
  }


  _closeDialog() {
    this._dialog = false;
    this._dialogError = "";
    this._render();
  }

  _groupLabel(group) {
    if (group === "downloaded") return "Downloaded";
    if (group === "available") return "Available for download";
    return this._typeLabel(group);
  }

  _typeLabel(type) {
    return {
      integration: "Integration",
      plugin: "Dashboard",
      theme: "Theme",
      python_script: "Python Script",
      appdaemon: "AppDaemon",
      template: "Template",
    }[type] || type;
  }

  _repoInitials(repo) {
    return this._escape((repo.name || repo.full_name || "LH").slice(0, 2).toUpperCase());
  }

  _escape(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    })[char]);
  }
}

customElements.define("lhacm-panel", LhacmPanel);
