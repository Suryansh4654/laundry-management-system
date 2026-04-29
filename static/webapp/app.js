const ROLE_CONTENT = {
    CUSTOMER: {
        title: "Customer login or signup",
        description: "Customer login selected. New signup will create a customer account.",
    },
    WORKER: {
        title: "Worker login or signup",
        description: "Worker login selected. New signup will create a worker account.",
    },
    ADMIN: {
        title: "Admin login or signup",
        description: "Admin login selected. New signup will create an admin account.",
    },
};

const STATUS_TRANSITIONS = {
    CUSTOMER: [],
    WORKER: {
        PENDING: ["ACCEPTED", "PROCESSING", "COMPLETED", "READY_FOR_DELIVERY"],
        ACCEPTED: ["PROCESSING", "COMPLETED", "READY_FOR_DELIVERY"],
        PROCESSING: ["COMPLETED", "READY_FOR_DELIVERY"],
        COMPLETED: ["READY_FOR_DELIVERY"],
        READY_FOR_DELIVERY: ["DELIVERED"],
    },
    ADMIN: {
        PENDING: ["ACCEPTED", "PROCESSING", "COMPLETED", "READY_FOR_DELIVERY", "CANCELLED"],
        ACCEPTED: ["PROCESSING", "COMPLETED", "READY_FOR_DELIVERY", "CANCELLED"],
        PROCESSING: ["COMPLETED", "READY_FOR_DELIVERY", "CANCELLED"],
        COMPLETED: ["READY_FOR_DELIVERY", "CANCELLED"],
        READY_FOR_DELIVERY: ["DELIVERED", "CANCELLED"],
        DELIVERED: [],
        CANCELLED: [],
    },
};

const state = {
    accessToken: localStorage.getItem("laundry_access_token"),
    refreshToken: localStorage.getItem("laundry_refresh_token"),
    currentUser: null,
    services: [],
    staff: [],
    issues: [],
    selectedRole: localStorage.getItem("laundry_selected_role") || "CUSTOMER",
    roleLocked: localStorage.getItem("laundry_role_locked") === "true",
};

const elements = {
    heroPanel: document.getElementById("heroPanel"),
    rolePanel: document.getElementById("rolePanel"),
    authPanel: document.getElementById("authPanel"),
    servicePanel: document.getElementById("servicePanel"),
    userPanel: document.getElementById("userPanel"),
    workerPanel: document.getElementById("workerPanel"),
    adminPanel: document.getElementById("adminPanel"),
    userBadge: document.getElementById("userBadge"),
    serviceGrid: document.getElementById("serviceGrid"),
    orderItems: document.getElementById("orderItems"),
    orderList: document.getElementById("orderList"),
    issueOrderSelect: document.getElementById("issueOrderSelect"),
    customerIssues: document.getElementById("customerIssues"),
    workerOrders: document.getElementById("workerOrders"),
    adminOrders: document.getElementById("adminOrders"),
    adminIssues: document.getElementById("adminIssues"),
    staffDirectory: document.getElementById("staffDirectory"),
    analyticsCards: document.getElementById("analyticsCards"),
    adminServiceList: document.getElementById("adminServiceList"),
    changeRoleButton: document.getElementById("changeRoleButton"),
    logoutButton: document.getElementById("logoutButton"),
    toast: document.getElementById("toast"),
    statusFilter: document.getElementById("statusFilter"),
    serviceCount: document.getElementById("serviceCount"),
    orderHelperText: document.getElementById("orderHelperText"),
    authTitle: document.getElementById("authTitle"),
    roleDescription: document.getElementById("roleDescription"),
};

const endpoints = {
    signup: "/api/auth/signup/",
    login: "/api/auth/login/",
    me: "/api/auth/me/",
    services: "/api/services/",
    orders: "/api/orders/",
    issues: "/api/issues/",
    staff: "/api/admin/staff/",
    analytics: "/api/admin/analytics/",
};

function normalizeCollection(payload) {
    return payload?.results || payload || [];
}

function roleLabel(role) {
    return role.charAt(0) + role.slice(1).toLowerCase();
}

function formatStatus(status) {
    if (status === "DELIVERED") {
        return "Delivered Successfully";
    }
    return status.replaceAll("_", " ");
}

async function apiFetch(url, options = {}, retry = true) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };

    if (state.accessToken) {
        headers.Authorization = `Bearer ${state.accessToken}`;
    }

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401 && state.refreshToken && retry) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            return apiFetch(url, options, false);
        }
    }

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : null;

    if (!response.ok) {
        throw new Error(formatApiError(payload));
    }

    return payload;
}

function flattenErrors(value, parentKey = "") {
    if (Array.isArray(value)) {
        return value.flatMap((item) => flattenErrors(item, parentKey));
    }

    if (value && typeof value === "object") {
        return Object.entries(value).flatMap(([key, nestedValue]) => {
            const nextKey = key === "detail" ? parentKey : key;
            return flattenErrors(nestedValue, nextKey);
        });
    }

    if (!value) {
        return [];
    }

    return [parentKey ? `${parentKey}: ${value}` : String(value)];
}

function formatApiError(payload) {
    const flattenedErrors = flattenErrors(payload?.errors || payload);
    return flattenedErrors[0] || payload?.message || payload?.detail || "Something went wrong.";
}

async function refreshAccessToken() {
    try {
        const response = await fetch("/api/auth/token/refresh/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh: state.refreshToken }),
        });
        if (!response.ok) {
            clearSession();
            return false;
        }
        const payload = await response.json();
        state.accessToken = payload.access;
        localStorage.setItem("laundry_access_token", payload.access);
        return true;
    } catch {
        clearSession();
        return false;
    }
}

function persistSession(payload) {
    state.accessToken = payload.access;
    state.refreshToken = payload.refresh;
    localStorage.setItem("laundry_access_token", payload.access);
    localStorage.setItem("laundry_refresh_token", payload.refresh);
}

function clearSession() {
    state.accessToken = null;
    state.refreshToken = null;
    state.currentUser = null;
    localStorage.removeItem("laundry_access_token");
    localStorage.removeItem("laundry_refresh_token");
    renderAuthState();
}

function showToast(message, isError = false) {
    elements.toast.textContent = message;
    elements.toast.classList.remove("hidden", "error");
    if (isError) {
        elements.toast.classList.add("error");
    }
    window.clearTimeout(showToast.timeout);
    showToast.timeout = window.setTimeout(() => {
        elements.toast.classList.add("hidden");
    }, 3200);
}

function setActiveTab(tabName) {
    document.querySelectorAll(".tab-button").forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === tabName);
    });
    document.getElementById("loginForm").classList.toggle("hidden", tabName !== "login");
    document.getElementById("signupForm").classList.toggle("hidden", tabName !== "signup");
}

function setSelectedRole(role, lockSelection = true) {
    state.selectedRole = role;
    localStorage.setItem("laundry_selected_role", role);
    if (lockSelection) {
        state.roleLocked = true;
        localStorage.setItem("laundry_role_locked", "true");
    }
    document.querySelectorAll(".role-card").forEach((button) => {
        button.classList.toggle("active", button.dataset.role === role);
    });
    elements.authTitle.textContent = ROLE_CONTENT[role].title;
    elements.roleDescription.textContent = ROLE_CONTENT[role].description;
    renderLayoutState();
}

function resetRoleSelection() {
    state.roleLocked = false;
    state.currentUser = null;
    localStorage.removeItem("laundry_role_locked");
    renderLayoutState();
}

function renderLayoutState() {
    const role = state.currentUser?.role || state.selectedRole;
    const showRoleSpecificOnly = state.roleLocked || Boolean(state.currentUser);

    elements.heroPanel.classList.toggle("hidden", showRoleSpecificOnly);
    elements.rolePanel.classList.toggle("hidden", showRoleSpecificOnly);
    elements.authPanel.classList.toggle("hidden", Boolean(state.currentUser) || !showRoleSpecificOnly);
    elements.servicePanel.classList.toggle("hidden", showRoleSpecificOnly || role !== "CUSTOMER");
    elements.changeRoleButton.classList.toggle("hidden", !showRoleSpecificOnly);
}

function getStatusClass(status) {
    return status.toLowerCase();
}

function renderServices() {
    const activeServices = state.services.filter((service) => service.is_active);
    elements.serviceCount.textContent = String(activeServices.length);

    if (!state.services.length) {
        elements.serviceGrid.innerHTML = `<article class="service-card"><p class="empty-state">No services available yet.</p></article>`;
        return;
    }

    elements.serviceGrid.innerHTML = state.services
        .filter((service) => service.is_active)
        .map(
            (service) => `
                <article class="service-card">
                    <div class="order-card-header">
                        <div>
                            <h4>${service.name}</h4>
                            <p class="service-meta">Ready to book</p>
                        </div>
                        <span class="service-price">₹${Number(service.price).toFixed(2)}</span>
                    </div>
                </article>
            `
        )
        .join("");
}

function renderAdminServices() {
    if (state.currentUser?.role !== "ADMIN") {
        elements.adminServiceList.innerHTML = "";
        return;
    }

    elements.adminServiceList.innerHTML = state.services
        .map(
            (service) => `
                <article class="service-card">
                    <h4>${service.name}</h4>
                    <label>Cost
                        <input class="small-input" type="number" step="0.01" min="0" data-service-price="${service.id}" value="${service.price}">
                    </label>
                    <div class="service-action-row">
                        <button class="secondary-button" data-save-service="${service.id}">Save</button>
                        <button class="secondary-button" data-toggle-service="${service.id}">
                            ${service.is_active ? "Deactivate" : "Activate"}
                        </button>
                    </div>
                </article>
            `
        )
        .join("");

    elements.adminServiceList.querySelectorAll("[data-save-service]").forEach((button) => {
        button.addEventListener("click", async () => {
            const id = button.dataset.saveService;
            const priceInput = elements.adminServiceList.querySelector(`[data-service-price="${id}"]`);
            await updateService(id, { price: priceInput.value });
        });
    });

    elements.adminServiceList.querySelectorAll("[data-toggle-service]").forEach((button) => {
        button.addEventListener("click", async () => {
            const id = button.dataset.toggleService;
            const currentService = state.services.find((service) => String(service.id) === String(id));
            await updateService(id, { is_active: !currentService.is_active });
        });
    });
}

function renderStaffDirectory() {
    if (state.currentUser?.role !== "ADMIN") {
        elements.staffDirectory.innerHTML = "";
        return;
    }
    elements.staffDirectory.innerHTML = state.staff
        .map(
            (member) => `
                <article class="order-card">
                    <h4>${member.username}</h4>
                    <p class="order-meta">${member.email}</p>
                    <span class="user-badge">${roleLabel(member.role)}</span>
                </article>
            `
        )
        .join("");
}

function addOrderItemRow(prefill = {}) {
    const row = document.createElement("div");
    row.className = "order-item-row";
    row.innerHTML = `
        <label>Service
            <select name="service" required>
                <option value="">Choose a service</option>
                ${state.services
                    .filter((service) => service.is_active)
                    .map(
                        (service) =>
                            `<option value="${service.id}" ${String(prefill.service_id) === String(service.id) ? "selected" : ""}>${service.name} - ₹${Number(service.price).toFixed(2)}</option>`
                    )
                    .join("")}
            </select>
        </label>
        <label>Garment
            <input type="text" name="garment_type" value="${prefill.garment_type || ""}" placeholder="Shirt / T-Shirt / Jeans" required>
        </label>
        <label>Quantity
            <input type="number" name="quantity" min="1" value="${prefill.quantity || 1}" required>
        </label>
        <button type="button" class="icon-button" aria-label="Remove row">✕</button>
    `;
    row.querySelector(".icon-button").addEventListener("click", () => row.remove());
    elements.orderItems.appendChild(row);
}

function syncServiceOptions() {
    const optionMarkup = `
        <option value="">Choose a service</option>
        ${state.services
            .filter((service) => service.is_active)
            .map((service) => `<option value="${service.id}">${service.name} - ₹${Number(service.price).toFixed(2)}</option>`)
            .join("")}
    `;

    elements.orderItems.querySelectorAll('select[name="service"]').forEach((select) => {
        const selectedValue = select.value;
        select.innerHTML = optionMarkup;
        if ([...select.options].some((option) => option.value === selectedValue)) {
            select.value = selectedValue;
        }
    });
}

function renderCustomerOrders(orders) {
    if (!orders.length) {
        elements.orderList.innerHTML = `<article class="order-card"><p class="empty-state">No orders found for this view yet.</p></article>`;
        return;
    }

    elements.orderList.innerHTML = orders
        .map(
            (order) => `
                <article class="order-card">
                    <div class="order-card-header">
                        <div>
                            <h4>Order #${order.id}</h4>
                            <p class="order-meta">Drop-off: ${order.drop_off_date} • Pickup: ${order.pickup_date}</p>
                            <p class="order-meta">Worker: ${order.assigned_worker ? order.assigned_worker.username : "Not assigned yet"}</p>
                            <p class="order-meta">Invoice: ${order.invoice_number} • Payment: ${formatStatus(order.payment_status)}</p>
                        </div>
                        <span class="status-pill ${getStatusClass(order.status)}">${formatStatus(order.status)}</span>
                    </div>
                    <ul class="order-lines">
                        ${order.order_items.map((item) => `<li>${item.garment_type} • ${item.service.name} x ${item.quantity} = ₹${Number(item.line_total).toFixed(2)}</li>`).join("")}
                    </ul>
                    <div class="order-card-footer">
                        <strong>Total: ₹${Number(order.total_price).toFixed(2)}</strong>
                        <span class="service-meta">Paid: ₹${Number(order.amount_paid).toFixed(2)}</span>
                        ${order.admin_note ? `<span class="service-meta">Admin note: ${order.admin_note}</span>` : ""}
                    </div>
                    <div class="timeline-list">
                        ${order.status_history.map((entry) => `<p class="order-meta">${formatStatus(entry.new_status)} • ${new Date(entry.created_at).toLocaleString()}</p>`).join("")}
                    </div>
                </article>
            `
        )
        .join("");

    elements.issueOrderSelect.innerHTML = orders
        .map((order) => `<option value="${order.id}">Order #${order.id} • ${formatStatus(order.status)}</option>`)
        .join("");
}

function renderCustomerIssues() {
    if (state.currentUser?.role !== "CUSTOMER") {
        elements.customerIssues.innerHTML = "";
        return;
    }
    if (!state.issues.length) {
        elements.customerIssues.innerHTML = `<article class="order-card"><p class="empty-state">No issues reported yet.</p></article>`;
        return;
    }
    elements.customerIssues.innerHTML = state.issues
        .map(
            (issue) => `
                <article class="order-card">
                    <h4>${formatStatus(issue.issue_type)}</h4>
                    <p class="order-meta">${issue.description}</p>
                    <p class="order-meta">Status: ${formatStatus(issue.status)}</p>
                    ${issue.resolution_note ? `<p class="order-meta">Resolution: ${issue.resolution_note}</p>` : ""}
                </article>
            `
        )
        .join("");
}

function renderOperationalOrders(target, orders, role) {
    if (!orders.length) {
        target.innerHTML = `<article class="order-card"><p class="empty-state">No orders available right now.</p></article>`;
        return;
    }

    target.innerHTML = orders
        .map((order) => {
            const allowedStatuses = [...new Set([order.status, ...(STATUS_TRANSITIONS[role][order.status] || [])])];
            const canDeliverNow = order.status === "READY_FOR_DELIVERY";
            return `
                <article class="order-card">
                    <div class="order-card-header">
                        <div>
                            <h4>Order #${order.id}</h4>
                            <p class="order-meta">Customer: ${order.user.username} • ${order.user.email}</p>
                            <p class="order-meta">Drop-off: ${order.drop_off_date} • Pickup: ${order.pickup_date}</p>
                            <p class="order-meta">Invoice: ${order.invoice_number}</p>
                        </div>
                        <span class="status-pill ${getStatusClass(order.status)}">${formatStatus(order.status)}</span>
                    </div>
                    <ul class="order-lines">
                        ${order.order_items.map((item) => `<li>${item.garment_type} • ${item.service.name} x ${item.quantity}</li>`).join("")}
                    </ul>
                    <div class="order-card-footer">
                        <strong>Total: ₹${Number(order.total_price).toFixed(2)}</strong>
                        <span class="service-meta">Payment: ${formatStatus(order.payment_status)}${order.payment_method ? ` • ${formatStatus(order.payment_method)}` : ""}</span>
                    </div>
                    <div class="order-action-grid">
                        <select data-order-status="${role}-${order.id}">
                            ${allowedStatuses.map((status) => `<option value="${status}" ${order.status === status ? "selected" : ""}>${formatStatus(status)}</option>`).join("")}
                        </select>
                        ${
                            role === "ADMIN"
                                ? `
                                    <select data-order-worker="${order.id}">
                                        <option value="">Unassigned worker</option>
                                        ${state.staff
                                            .filter((member) => member.role === "WORKER")
                                            .map((member) => `<option value="${member.id}" ${order.assigned_worker?.id === member.id ? "selected" : ""}>${member.username}</option>`)
                                            .join("")}
                                    </select>
                                    <select data-payment-status="${order.id}">
                                        ${["UNPAID", "PAID", "REFUNDED"].map((status) => `<option value="${status}" ${order.payment_status === status ? "selected" : ""}>${formatStatus(status)}</option>`).join("")}
                                    </select>
                                    <select data-payment-method="${order.id}">
                                        <option value="">Select payment method</option>
                                        ${["CASH", "UPI", "CARD", "BANK_TRANSFER"].map((method) => `<option value="${method}" ${order.payment_method === method ? "selected" : ""}>${formatStatus(method)}</option>`).join("")}
                                    </select>
                                `
                                : ""
                        }
                        ${
                            role === "ADMIN"
                                ? `<textarea class="small-input" data-order-note="${order.id}" placeholder="Issue note / correction">${order.admin_note || ""}</textarea>`
                                : ""
                        }
                        <button class="secondary-button" data-save-order="${role}-${order.id}">Save</button>
                        ${
                            role === "ADMIN"
                                ? `<button class="secondary-button" data-delete-order="${order.id}">Delete</button>`
                                : ""
                        }
                    </div>
                    ${
                        canDeliverNow
                            ? `
                                <div class="delivery-verify">
                                    <input class="small-input" type="password" data-delivery-password="${role}-${order.id}" placeholder="Enter customer password to deliver">
                                    <button class="primary-button" data-deliver-order="${role}-${order.id}">Deliver successfully</button>
                                </div>
                              `
                            : ""
                    }
                    <div class="timeline-list">
                        ${order.status_history.map((entry) => `<p class="order-meta">${formatStatus(entry.new_status)} by ${entry.changed_by ? entry.changed_by.username : "System"} • ${new Date(entry.created_at).toLocaleString()}</p>`).join("")}
                    </div>
                </article>
            `;
        })
        .join("");

    target.querySelectorAll("[data-save-order]").forEach((button) => {
        button.addEventListener("click", async () => {
            const key = button.dataset.saveOrder;
            const [mode, orderId] = key.split("-");
            const statusValue = target.querySelector(`[data-order-status="${key}"]`).value;
            const payload = {};
            if (statusValue) {
                payload.status = statusValue;
            }
            if (mode === "ADMIN") {
                payload.admin_note = target.querySelector(`[data-order-note="${orderId}"]`).value;
                payload.assigned_worker_id = target.querySelector(`[data-order-worker="${orderId}"]`).value || null;
                payload.payment_status = target.querySelector(`[data-payment-status="${orderId}"]`).value;
                payload.payment_method = target.querySelector(`[data-payment-method="${orderId}"]`).value;
            }
            if (!payload.status && mode !== "ADMIN") {
                showToast("Select a valid status before saving.", true);
                return;
            }
            await updateOperationalOrder(mode, orderId, payload);
        });
    });

    target.querySelectorAll("[data-deliver-order]").forEach((button) => {
        button.addEventListener("click", async () => {
            const key = button.dataset.deliverOrder;
            const [mode, orderId] = key.split("-");
            const passwordValue = target.querySelector(`[data-delivery-password="${key}"]`).value;
            if (!passwordValue) {
                showToast("Enter customer password to complete delivery.", true);
                return;
            }

            const payload = {
                status: "DELIVERED",
                verification_password: passwordValue,
            };
            if (mode === "ADMIN") {
                payload.admin_note = target.querySelector(`[data-order-note="${orderId}"]`)?.value || "";
            }
            await updateOperationalOrder(mode, orderId, payload);
        });
    });

    if (role === "ADMIN") {
        target.querySelectorAll("[data-delete-order]").forEach((button) => {
            button.addEventListener("click", async () => {
                await deleteOrder(button.dataset.deleteOrder);
            });
        });
    }
}

function renderAnalytics(payload) {
    const cards = [
        ["Total orders", payload.total_orders],
        ["Delivered", payload.delivered_orders],
        ["Pending", payload.pending_orders],
        ["Ready for delivery", payload.ready_for_delivery_orders],
        ["Paid orders", payload.paid_orders],
        ["Open issues", payload.open_issues],
        ["Revenue", `₹${Number(payload.total_revenue).toFixed(2)}`],
    ];

    elements.analyticsCards.innerHTML = cards
        .map(
            ([label, value]) => `
                <article class="metric-card">
                    <span>${label}</span>
                    <strong>${value}</strong>
                </article>
            `
        )
        .join("");
}

function renderAdminIssues() {
    if (state.currentUser?.role !== "ADMIN") {
        elements.adminIssues.innerHTML = "";
        return;
    }
    if (!state.issues.length) {
        elements.adminIssues.innerHTML = `<article class="order-card"><p class="empty-state">No open issues right now.</p></article>`;
        return;
    }
    elements.adminIssues.innerHTML = state.issues
        .map(
            (issue) => `
                <article class="order-card">
                    <h4>${formatStatus(issue.issue_type)}</h4>
                    <p class="order-meta">${issue.description}</p>
                    <p class="order-meta">Status: ${formatStatus(issue.status)}</p>
                    <textarea class="small-input" data-issue-note="${issue.id}" placeholder="Resolution note">${issue.resolution_note || ""}</textarea>
                    <div class="service-action-row">
                        <select data-issue-status="${issue.id}">
                            ${["OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED"].map((status) => `<option value="${status}" ${issue.status === status ? "selected" : ""}>${formatStatus(status)}</option>`).join("")}
                        </select>
                        <button class="secondary-button" data-save-issue="${issue.id}">Save issue</button>
                    </div>
                </article>
            `
        )
        .join("");

    elements.adminIssues.querySelectorAll("[data-save-issue]").forEach((button) => {
        button.addEventListener("click", async () => {
            const issueId = button.dataset.saveIssue;
            await updateIssue(issueId, {
                status: elements.adminIssues.querySelector(`[data-issue-status="${issueId}"]`).value,
                resolution_note: elements.adminIssues.querySelector(`[data-issue-note="${issueId}"]`).value,
            });
        });
    });
}

function renderAuthState() {
    const role = state.currentUser?.role;
    const isLoggedIn = Boolean(state.currentUser);
    elements.userPanel.classList.toggle("hidden", role !== "CUSTOMER");
    elements.workerPanel.classList.toggle("hidden", role !== "WORKER");
    elements.adminPanel.classList.toggle("hidden", role !== "ADMIN");
    elements.logoutButton.classList.toggle("hidden", !isLoggedIn);

    if (isLoggedIn) {
        elements.userBadge.textContent = `${state.currentUser.username} • ${roleLabel(role)}`;
    } else {
        elements.userBadge.textContent = "";
        elements.orderList.innerHTML = "";
        elements.workerOrders.innerHTML = "";
        elements.adminOrders.innerHTML = "";
        elements.analyticsCards.innerHTML = "";
        elements.adminServiceList.innerHTML = "";
    }

    renderLayoutState();
    updateOrderHelper();
}

function updateOrderHelper() {
    if (state.currentUser?.role !== "CUSTOMER") {
        elements.orderHelperText.textContent = "";
        elements.orderHelperText.classList.add("hidden");
        return;
    }

    if (!state.services.some((service) => service.is_active)) {
        elements.orderHelperText.textContent = "No active services are available yet. Wait for admin to add or activate services.";
        elements.orderHelperText.classList.remove("hidden");
        return;
    }

    elements.orderHelperText.textContent = "Add garment type, quantity, and confirm with your account password before handing clothes to laundry.";
    elements.orderHelperText.classList.remove("hidden");
}

async function loadServices() {
    const payload = await apiFetch(endpoints.services, { method: "GET" });
    state.services = normalizeCollection(payload);
    renderServices();
    renderAdminServices();
    if (!elements.orderItems.children.length) {
        addOrderItemRow();
    } else {
        syncServiceOptions();
    }
    updateOrderHelper();
}

async function loadProfile() {
    if (!state.accessToken) {
        renderAuthState();
        return;
    }

    try {
        state.currentUser = await apiFetch(endpoints.me, { method: "GET" });
        renderAuthState();
        await loadRoleData();
    } catch {
        clearSession();
    }
}

async function loadRoleData() {
    if (!state.currentUser) {
        return;
    }

    if (state.currentUser.role === "CUSTOMER") {
        await Promise.all([loadCustomerOrders(), loadIssues()]);
        return;
    }

    if (state.currentUser.role === "WORKER") {
        await Promise.all([loadWorkerOrders(), loadAnalytics(), loadIssues()]);
        return;
    }

    if (state.currentUser.role === "ADMIN") {
        await Promise.all([loadAnalytics(), loadServices(), loadStaff(), loadIssues()]);
        await loadAdminOrders();
    }
}

async function loadCustomerOrders() {
    const status = elements.statusFilter.value;
    const url = status ? `${endpoints.orders}?status=${status}` : endpoints.orders;
    const payload = await apiFetch(url, { method: "GET" });
    renderCustomerOrders(normalizeCollection(payload));
}

async function loadWorkerOrders() {
    const payload = await apiFetch(endpoints.orders, { method: "GET" });
    const orders = normalizeCollection(payload).filter((order) => order.status !== "DELIVERED" && order.status !== "CANCELLED");
    renderOperationalOrders(elements.workerOrders, orders, "WORKER");
}

async function loadAdminOrders() {
    const payload = await apiFetch(endpoints.orders, { method: "GET" });
    renderOperationalOrders(elements.adminOrders, normalizeCollection(payload), "ADMIN");
}

async function loadAnalytics() {
    const payload = await apiFetch(endpoints.analytics, { method: "GET" });
    renderAnalytics(payload);
}

async function loadStaff() {
    if (state.currentUser?.role !== "ADMIN") {
        return;
    }
    const payload = await apiFetch(endpoints.staff, { method: "GET" });
    state.staff = normalizeCollection(payload);
    renderStaffDirectory();
}

async function loadIssues() {
    if (!state.currentUser) {
        return;
    }
    const payload = await apiFetch(endpoints.issues, { method: "GET" });
    state.issues = normalizeCollection(payload);
    renderCustomerIssues();
    renderAdminIssues();
}

async function updateOperationalOrder(role, orderId, payload) {
    const endpoint = role === "ADMIN"
        ? `/api/admin/orders/${orderId}/manage/`
        : `/api/worker/orders/${orderId}/status/`;
    try {
        await apiFetch(endpoint, {
            method: "PATCH",
            body: JSON.stringify(payload),
        });
        showToast("Order updated successfully.");
        await loadRoleData();
    } catch (error) {
        showToast(error.message, true);
    }
}

async function updateService(serviceId, payload) {
    try {
        await apiFetch(`/api/services/${serviceId}/`, {
            method: "PATCH",
            body: JSON.stringify(payload),
        });
        showToast("Service updated.");
        await loadServices();
    } catch (error) {
        showToast(error.message, true);
    }
}

async function deleteOrder(orderId) {
    try {
        await apiFetch(`/api/orders/${orderId}/`, { method: "DELETE" });
        showToast("Order deleted.");
        await loadAdminOrders();
        await loadAnalytics();
    } catch (error) {
        showToast(error.message, true);
    }
}

async function updateIssue(issueId, payload) {
    try {
        await apiFetch(`/api/issues/${issueId}/`, {
            method: "PATCH",
            body: JSON.stringify(payload),
        });
        showToast("Issue updated.");
        await loadIssues();
    } catch (error) {
        showToast(error.message, true);
    }
}

document.getElementById("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    try {
        const payload = await apiFetch(endpoints.login, {
            method: "POST",
            body: JSON.stringify({
                email: formData.get("email"),
                password: formData.get("password"),
                role: state.selectedRole,
            }),
        });
        persistSession(payload);
        state.currentUser = payload.user;
        form.reset();
        renderAuthState();
        showToast(`Welcome back, ${payload.user.username}.`);
        await loadRoleData();
    } catch (error) {
        showToast(error.message, true);
    }
});

document.getElementById("signupForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    try {
        await apiFetch(endpoints.signup, {
            method: "POST",
            body: JSON.stringify({
                email: formData.get("email"),
                username: formData.get("username"),
                password: formData.get("password"),
                confirm_password: formData.get("confirm_password"),
                role: state.selectedRole,
            }),
        });
        form.reset();
        showToast(`${roleLabel(state.selectedRole)} account created. You can log in now.`);
        setActiveTab("login");
    } catch (error) {
        showToast(error.message, true);
    }
});

document.getElementById("orderForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const rows = [...elements.orderItems.querySelectorAll(".order-item-row")];
    const items = rows.map((row) => ({
        service_id: Number(row.querySelector('[name="service"]').value),
        garment_type: row.querySelector('[name="garment_type"]').value.trim(),
        quantity: Number(row.querySelector('[name="quantity"]').value),
    }));

    if (items.some((item) => !item.service_id || !item.garment_type || !item.quantity)) {
        showToast("Fill all garment rows before submitting.", true);
        return;
    }

    try {
        const formData = new FormData(form);
        await apiFetch(endpoints.orders, {
            method: "POST",
            body: JSON.stringify({
                drop_off_date: formData.get("drop_off_date"),
                pickup_date: formData.get("pickup_date"),
                account_password: formData.get("account_password"),
                items,
            }),
        });
        form.reset();
        elements.orderItems.innerHTML = "";
        addOrderItemRow();
        syncDateMinimums();
        showToast("Order placed successfully.");
        await loadCustomerOrders();
    } catch (error) {
        showToast(error.message, true);
    }
});

document.getElementById("serviceForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    try {
        await apiFetch(endpoints.services, {
            method: "POST",
            body: JSON.stringify({
                name: formData.get("name"),
                price: formData.get("price"),
                is_active: true,
            }),
        });
        form.reset();
        showToast("Service created.");
        await loadServices();
    } catch (error) {
        showToast(error.message, true);
    }
});

document.getElementById("staffAccountForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    try {
        await apiFetch(endpoints.signup, {
            method: "POST",
            body: JSON.stringify({
                email: formData.get("email"),
                username: formData.get("username"),
                password: formData.get("password"),
                confirm_password: formData.get("confirm_password"),
                role: formData.get("role"),
            }),
        });
        form.reset();
        showToast(`${roleLabel(formData.get("role"))} account created successfully.`);
        await loadStaff();
    } catch (error) {
        showToast(error.message, true);
    }
});

document.getElementById("issueForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    try {
        await apiFetch(endpoints.issues, {
            method: "POST",
            body: JSON.stringify({
                order_id: formData.get("order_id"),
                issue_type: formData.get("issue_type"),
                description: formData.get("description"),
            }),
        });
        form.reset();
        showToast("Issue submitted.");
        await loadIssues();
    } catch (error) {
        showToast(error.message, true);
    }
});

function syncDateMinimums() {
    const today = new Date().toISOString().split("T")[0];
    const dropOffInput = document.querySelector('#orderForm input[name="drop_off_date"]');
    const pickupInput = document.querySelector('#orderForm input[name="pickup_date"]');
    if (dropOffInput) {
        dropOffInput.min = today;
        dropOffInput.addEventListener("change", () => {
            pickupInput.min = dropOffInput.value || today;
        });
    }
    if (pickupInput) {
        pickupInput.min = dropOffInput?.value || today;
    }
}

document.getElementById("refreshServicesButton").addEventListener("click", loadServices);
document.getElementById("refreshAnalyticsButton").addEventListener("click", loadAnalytics);
document.getElementById("refreshAllOrdersButton").addEventListener("click", loadAdminOrders);
document.getElementById("refreshWorkerOrdersButton").addEventListener("click", loadWorkerOrders);
document.getElementById("addItemButton").addEventListener("click", () => addOrderItemRow());
elements.statusFilter.addEventListener("change", loadCustomerOrders);
elements.logoutButton.addEventListener("click", () => {
    clearSession();
    showToast("You have been logged out.");
});
elements.changeRoleButton.addEventListener("click", () => {
    clearSession();
    resetRoleSelection();
});

document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
});

document.querySelectorAll(".role-card").forEach((button) => {
    button.addEventListener("click", () => setSelectedRole(button.dataset.role));
});

setSelectedRole(state.selectedRole, state.roleLocked);
renderLayoutState();
syncDateMinimums();
Promise.all([loadServices(), loadProfile()]).catch((error) => showToast(error.message, true));
