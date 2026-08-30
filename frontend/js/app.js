function taskTrackerApp() {
    return {
        // State
        token: localStorage.getItem('tt_token') || '',
        currentUser: JSON.parse(localStorage.getItem('tt_user') || '{}'),
        activeTab: 'cabinet', // 'cabinet', 'kanban', 'list', 'bugs'
        darkMode: localStorage.getItem('tt_dark') === 'true',

        // Auth state
        authMode: 'login', // 'login' | 'register'
        authError: '',
        loginForm: { username: '', password: '' },
        registerForm: { username: '', full_name: '', email: '', role: 'Разработчик', password: '' },

        // Data lists
        tasks: [],
        usersList: [],
        userActivities: [],
        userStats: { total_assigned: 0, in_progress: 0, completed: 0, urgent: 0, created_by_me: 0, open_bugs_count: 0 },
        fullStats: { total_tasks: 0, completed_tasks: 0, tasks_completion_rate: 0, total_bugs: 0, fixed_bugs: 0, bugs_resolution_rate: 0, critical_bugs: 0, status_breakdown: {}, bug_severity_breakdown: {}, priority_breakdown: {}, user_performance: [] },
        
        // Calendar State
        calendarDate: new Date(),
        filterCalendarType: '',

        // Filters
        searchQuery: '',
        filterMyOnly: true,
        filterPriority: '',
        filterAssignee: '',
        filterBugSeverity: '',
        filterBugStatus: '',
        bugViewMode: 'list', // 'list' | 'cards'

        userMenuOpen: false,
        notificationMenuOpen: false,
        notifications: [],

        // Subtasks & AI & Media Preview
        newSubtaskTitle: '',
        isGeneratingSubtasks: false,
        isSummarizing: false,
        aiSummaryResult: '',
        activeMediaPreview: null,

        // Modals
        showDetailModal: false,
        showUserProfileModal: false,
        showEditProfileModal: false,
        showAdminAddUserModal: false,
        showAdminEditUserModal: false,
        editingUserObj: null,
        adminAddUserForm: { username: '', full_name: '', password: '', email: '', role: 'Разработчик', role_description: '', payment_details: '' },
        adminEditUserForm: { username: '', full_name: '', password: '', email: '', role: '', role_description: '', payment_details: '', avatar_color: '#3b82f6' },
        savingProfile: false,
        selectedUserProfile: null,
        editProfileForm: {
            full_name: '',
            email: '',
            role: '',
            role_description: '',
            payment_details: '',
            avatar_color: '#3b82f6'
        },
        activeTask: {},
        activeComments: [],
        newCommentText: '',
        uploadingFile: false,

        showCreateModal: false,
        submittingTask: false,
        showReopenModal: false,
        reopenReason: '',
        createTaskPendingFiles: [],
        createTaskForm: {
            title: '',
            description: '',
            status: 'todo',
            priority: 'medium',
            assignee_id: null,
            due_date: '',
            tags: '',
            task_type: 'task',
            severity: 'major',
            steps_to_reproduce: ''
        },

        kanbanColumns: [
            { status: 'todo', title: 'Новая', color: 'bg-slate-400' },
            { status: 'in_progress', title: 'В работе', color: 'bg-amber-500' },
            { status: 'in_review', title: 'На проверке', color: 'bg-blue-500' },
            { status: 'done', title: 'Завершена', color: 'bg-emerald-500' },
            { status: 'on_hold', title: 'Отложена', color: 'bg-purple-500' }
        ],

        get isAuthenticated() {
            return !!this.token;
        },

        get isAdmin() {
            if (!this.currentUser) return false;
            return this.currentUser.role === 'Администратор' || this.currentUser.username === 'admin' || this.currentUser.username === 'anjey';
        },

        get myActiveTasks() {
            if (!this.currentUser || !this.currentUser.id) return [];
            return this.tasks.filter(t => t.assignee_id === this.currentUser.id && t.status !== 'done');
        },

        get allBugs() {
            return this.tasks.filter(t => t.task_type === 'bug');
        },

        get filteredBugs() {
            return this.allBugs.filter(b => {
                if (this.filterBugStatus && b.status !== this.filterBugStatus) return false;
                if (this.filterBugSeverity && b.severity !== this.filterBugSeverity) return false;
                if (this.filterAssignee && b.assignee_id != this.filterAssignee) return false;
                if (this.searchQuery) {
                    const q = this.searchQuery.toLowerCase();
                    return b.title.toLowerCase().includes(q) || (b.description && b.description.toLowerCase().includes(q)) || (b.tags && b.tags.toLowerCase().includes(q));
                }
                return true;
            });
        },

        // Calendar Getters & Methods
        get calendarTitle() {
            const months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
            return `${months[this.calendarDate.getMonth()]} ${this.calendarDate.getFullYear()}`;
        },

        get calendarDays() {
            const year = this.calendarDate.getFullYear();
            const month = this.calendarDate.getMonth();
            
            const firstDayOfMonth = new Date(year, month, 1);
            const lastDayOfMonth = new Date(year, month + 1, 0);

            let firstDayOfWeek = firstDayOfMonth.getDay();
            if (firstDayOfWeek === 0) firstDayOfWeek = 7;

            const daysInMonth = lastDayOfMonth.getDate();
            const daysInPrevMonth = new Date(year, month, 0).getDate();

            const todayStr = this.formatDateISO(new Date());
            const days = [];

            for (let i = firstDayOfWeek - 1; i > 0; i--) {
                const d = daysInPrevMonth - i + 1;
                const prevDate = new Date(year, month - 1, d);
                const dateStr = this.formatDateISO(prevDate);
                days.push({
                    dateStr: dateStr,
                    dayNumber: d,
                    isCurrentMonth: false,
                    isToday: dateStr === todayStr,
                    tasks: this.getTasksForDate(dateStr)
                });
            }

            for (let d = 1; d <= daysInMonth; d++) {
                const currDate = new Date(year, month, d);
                const dateStr = this.formatDateISO(currDate);
                days.push({
                    dateStr: dateStr,
                    dayNumber: d,
                    isCurrentMonth: true,
                    isToday: dateStr === todayStr,
                    tasks: this.getTasksForDate(dateStr)
                });
            }

            const totalCells = days.length > 35 ? 42 : 35;
            const remaining = totalCells - days.length;
            for (let d = 1; d <= remaining; d++) {
                const nextDate = new Date(year, month + 1, d);
                const dateStr = this.formatDateISO(nextDate);
                days.push({
                    dateStr: dateStr,
                    dayNumber: d,
                    isCurrentMonth: false,
                    isToday: dateStr === todayStr,
                    tasks: this.getTasksForDate(dateStr)
                });
            }

            return days;
        },

        formatDateISO(d) {
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${y}-${m}-${day}`;
        },

        getTasksForDate(dateStr) {
            if (!dateStr) return [];
            return this.tasks.filter(t => {
                if (!t.due_date) return false;
                if (t.due_date !== dateStr) return false;
                if (this.filterCalendarType && t.task_type !== this.filterCalendarType) return false;
                return true;
            });
        },

        prevCalendarMonth() {
            this.calendarDate = new Date(this.calendarDate.getFullYear(), this.calendarDate.getMonth() - 1, 1);
            this.refreshIcons();
        },

        nextCalendarMonth() {
            this.calendarDate = new Date(this.calendarDate.getFullYear(), this.calendarDate.getMonth() + 1, 1);
            this.refreshIcons();
        },

        todayCalendarMonth() {
            this.calendarDate = new Date();
            this.refreshIcons();
        },

        init() {
            this.$watch('darkMode', val => localStorage.setItem('tt_dark', val));
            this.$nextTick(() => lucide.createIcons());

            if (this.token) {
                this.loadInitialData().catch(err => {
                    console.warn("Initial data load error:", err);
                });
            }
        },

        refreshIcons() {
            setTimeout(() => lucide.createIcons(), 50);
        },

        // API Helper with Bearer Token
        async apiFetch(url, options = {}) {
            options.headers = options.headers || {};
            const isAuthRoute = url.includes('/api/auth/login') || url.includes('/api/auth/register');
            if (this.token && !isAuthRoute && !options.skipAuth) {
                options.headers['Authorization'] = `Bearer ${this.token}`;
            }
            if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
                options.headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(options.body);
            }

            const response = await fetch(url, options);
            if (response.status === 401 && !isAuthRoute) {
                this.logout();
                throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
            }
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                let detailMsg = errData.detail;
                if (detailMsg && typeof detailMsg === 'object') {
                    if (Array.isArray(detailMsg)) {
                        detailMsg = detailMsg.map(d => d.msg || d.detail || JSON.stringify(d)).join(', ');
                    } else {
                        detailMsg = JSON.stringify(detailMsg);
                    }
                }
                throw new Error(detailMsg || `Ошибка сервера: ${response.status}`);
            }
            if (response.status === 204) return null;
            return await response.json();
        },

        // Auth Logic
        async login() {
            this.authError = '';
            try {
                const data = await this.apiFetch('/api/auth/login', {
                    method: 'POST',
                    body: this.loginForm
                });
                this.setAuthSession(data.access_token, data.user);
            } catch (err) {
                this.authError = err.message;
            }
        },

        async register() {
            this.authError = '';
            try {
                const data = await this.apiFetch('/api/auth/register', {
                    method: 'POST',
                    body: this.registerForm
                });
                this.setAuthSession(data.access_token, data.user);
            } catch (err) {
                this.authError = err.message;
            }
        },

        quickLogin(username, password) {
            this.loginForm.username = username;
            this.loginForm.password = password;
            this.login();
        },

        setAuthSession(token, user) {
            this.token = token;
            this.currentUser = user;
            localStorage.setItem('tt_token', token);
            localStorage.setItem('tt_user', JSON.stringify(user));
            this.loginForm = { username: '', password: '' };
            this.registerForm = { username: '', full_name: '', role: 'Разработчик', password: '' };
            this.loadInitialData();
        },

        logout() {
            this.token = '';
            this.currentUser = {};
            localStorage.removeItem('tt_token');
            localStorage.removeItem('tt_user');
            this.tasks = [];
        },

        get onlineUsersCount() {
            if (!this.usersList) return 0;
            return this.usersList.filter(u => u.is_online).length;
        },

        // Load Data
        async loadInitialData() {
            await Promise.all([
                this.fetchUsers(),
                this.fetchTasks(),
                this.fetchUserStats(),
                this.fetchFullStats(),
                this.fetchUserActivities(),
                this.fetchNotifications()
            ]);
            this.startHeartbeat();
            this.refreshIcons();
        },

        startHeartbeat() {
            if (this._pingInterval) clearInterval(this._pingInterval);
            this._pingInterval = setInterval(() => {
                if (this.isAuthenticated) {
                    this.apiFetch('/api/auth/ping', { method: 'POST' }).catch(() => {});
                    this.fetchUsers();
                    this.fetchUserActivities();
                    this.fetchNotifications();
                }
            }, 20000);
        },

        async fetchUsers() {
            try {
                this.usersList = await this.apiFetch('/api/users');
                if (this.currentUser && this.currentUser.id) {
                    const freshMe = this.usersList.find(u => u.id === this.currentUser.id);
                    if (freshMe && freshMe.avatar_url !== undefined) {
                        this.currentUser.avatar_url = freshMe.avatar_url;
                        localStorage.setItem('tt_user', JSON.stringify(this.currentUser));
                    }
                }
            } catch (e) { console.error(e); }
        },

        async fetchUserActivities() {
            try {
                this.userActivities = await this.apiFetch('/api/admin/activity');
            } catch (e) { console.error(e); }
        },

        async fetchUserStats() {
            try {
                this.userStats = await this.apiFetch('/api/stats/my-summary');
            } catch (e) { console.error(e); }
        },

        async fetchFullStats() {
            try {
                this.fullStats = await this.apiFetch('/api/stats/full');
            } catch (e) { console.error(e); }
        },

        async fetchTasks() {
            try {
                const params = new URLSearchParams();
                if (this.filterMyOnly) params.append('my_tasks_only', 'true');
                if (this.filterPriority) params.append('priority', this.filterPriority);
                if (this.filterAssignee) params.append('assignee_id', this.filterAssignee);
                if (this.searchQuery) params.append('search', this.searchQuery);

                this.tasks = await this.apiFetch(`/api/tasks?${params.toString()}`);
                this.refreshIcons();
            } catch (e) { console.error(e); }
        },

        // Kanban Helpers
        getTasksByStatus(status) {
            return this.tasks.filter(t => t.status === status);
        },

        async changeTaskStatus(taskId, newStatus) {
            try {
                const updated = await this.apiFetch(`/api/tasks/${taskId}`, {
                    method: 'PATCH',
                    body: { status: newStatus }
                });
                const idx = this.tasks.findIndex(t => t.id === taskId);
                if (idx !== -1) this.tasks[idx] = updated;
                this.fetchUserStats();
                this.refreshIcons();
            } catch (e) { alert(e.message); }
        },

        async completeActiveTask() {
            if (!this.activeTask || !this.activeTask.id) return;
            try {
                const updated = await this.apiFetch(`/api/tasks/${this.activeTask.id}`, {
                    method: 'PATCH',
                    body: { status: 'done' }
                });
                this.activeTask = updated;
                const idx = this.tasks.findIndex(t => t.id === updated.id);
                if (idx !== -1) this.tasks[idx] = updated;
                this.fetchUserStats();
                this.fetchFullStats();
                this.refreshIcons();
            } catch (e) { alert(e.message); }
        },

        openReopenModal() {
            this.reopenReason = '';
            this.showReopenModal = true;
        },

        async confirmReopenTask() {
            if (!this.activeTask || !this.activeTask.id) return;
            const reason = this.reopenReason.trim() || 'Без указания причины';
            try {
                // 1. Update status to in_progress
                const updated = await this.apiFetch(`/api/tasks/${this.activeTask.id}`, {
                    method: 'PATCH',
                    body: { status: 'in_progress' }
                });
                this.activeTask = updated;

                // 2. Post comment with return reason
                const comm = await this.apiFetch(`/api/tasks/${this.activeTask.id}/comments`, {
                    method: 'POST',
                    body: { content: `⏪ **Задача возвращена в работу**\nПричина: ${reason}` }
                });
                if (!this.activeComments) this.activeComments = [];
                this.activeComments.push(comm);
                this.activeTask.comments_count = (this.activeTask.comments_count || 0) + 1;

                // 3. Sync state
                const idx = this.tasks.findIndex(t => t.id === updated.id);
                if (idx !== -1) {
                    this.tasks[idx] = updated;
                    this.tasks[idx].comments_count = this.activeTask.comments_count;
                }

                this.showReopenModal = false;
                this.reopenReason = '';
                this.fetchUserStats();
                this.fetchFullStats();
                this.refreshIcons();
            } catch (e) { alert(e.message); }
        },

        // Drag & Drop Kanban State & Methods
        draggedTaskId: null,
        dragOverStatus: null,

        handleDragStart(e, task) {
            this.draggedTaskId = task.id;
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', task.id);
        },

        handleDragEnd(e) {
            this.draggedTaskId = null;
            this.dragOverStatus = null;
        },

        handleDragOver(e, status) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.dragOverStatus = status;
        },

        handleDragLeave(e, status) {
            if (this.dragOverStatus === status) {
                this.dragOverStatus = null;
            }
        },

        async handleDrop(e, targetStatus) {
            e.preventDefault();
            const taskId = this.draggedTaskId || parseInt(e.dataTransfer.getData('text/plain'));
            this.dragOverStatus = null;
            this.draggedTaskId = null;

            if (!taskId) return;

            const task = this.tasks.find(t => t.id === taskId);
            if (task && task.status !== targetStatus) {
                // Optimistic UI update
                task.status = targetStatus;
                await this.changeTaskStatus(taskId, targetStatus);
                this.fetchFullStats();
            }
        },

        moveTaskNext(task) {
            const flow = ['todo', 'in_progress', 'in_review', 'done', 'on_hold'];
            const currIdx = flow.indexOf(task.status);
            if (currIdx < flow.length - 1) {
                this.changeTaskStatus(task.id, flow[currIdx + 1]);
            }
        },

        moveTaskPrev(task) {
            const flow = ['todo', 'in_progress', 'in_review', 'done', 'on_hold'];
            const currIdx = flow.indexOf(task.status);
            if (currIdx > 0) {
                this.changeTaskStatus(task.id, flow[currIdx - 1]);
            }
        },

        // Task Detail & Editing
        async openTaskDetail(taskId) {
            try {
                this.activeTask = await this.apiFetch(`/api/tasks/${taskId}`);
                if (!this.activeTask.attachments) this.activeTask.attachments = [];
                this.activeComments = await this.apiFetch(`/api/tasks/${taskId}/comments`);
                this.showDetailModal = true;
                this.refreshIcons();
            } catch (e) { alert(e.message); }
        },

        async updateActiveTaskField(field, val) {
            try {
                const payload = {};
                payload[field] = val;
                const updated = await this.apiFetch(`/api/tasks/${this.activeTask.id}`, {
                    method: 'PATCH',
                    body: payload
                });
                this.activeTask = updated;
                const idx = this.tasks.findIndex(t => t.id === updated.id);
                if (idx !== -1) this.tasks[idx] = updated;
                this.fetchUserStats();
            } catch (e) { alert(e.message); }
        },

        async deleteTask(taskId) {
            if (!confirm('Вы действительно хотите удалить эту задачу/баг?')) return;
            try {
                await this.apiFetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
                this.showDetailModal = false;
                this.fetchTasks();
                this.fetchUserStats();
            } catch (e) { alert(e.message); }
        },

        // Attachments Logic
        async uploadAttachment(event) {
            const files = Array.from(event.target.files);
            if (!files.length) return;

            this.uploadingFile = true;
            try {
                const formData = new FormData();
                for (const file of files) {
                    formData.append('files', file);
                }

                const response = await fetch(`/api/tasks/${this.activeTask.id}/attachments/batch`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.token}`
                    },
                    body: formData
                });

                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.detail || 'Ошибка загрузки файлов');
                }

                const newAttachments = await response.json();
                if (!this.activeTask.attachments) this.activeTask.attachments = [];
                this.activeTask.attachments.push(...newAttachments);
                
                // Update in task list
                const idx = this.tasks.findIndex(t => t.id === this.activeTask.id);
                if (idx !== -1) this.tasks[idx].attachments = this.activeTask.attachments;

                event.target.value = '';
                this.refreshIcons();
            } catch (e) {
                alert(e.message);
            } finally {
                this.uploadingFile = false;
            }
        },

        async uploadChatAttachment(event) {
            const files = Array.from(event.target.files);
            if (!files.length) return;

            await this.uploadAttachment(event);

            const filenames = files.map(f => f.name).join(', ');
            try {
                const comm = await this.apiFetch(`/api/tasks/${this.activeTask.id}/comments`, {
                    method: 'POST',
                    body: { content: `📎 **Прикреплен(ы) файл(ы):** ${filenames}` }
                });
                if (!this.activeComments) this.activeComments = [];
                this.activeComments.push(comm);
                this.activeTask.comments_count = (this.activeTask.comments_count || 0) + 1;
                const idx = this.tasks.findIndex(t => t.id === this.activeTask.id);
                if (idx !== -1) this.tasks[idx].comments_count = this.activeTask.comments_count;
                this.refreshIcons();
            } catch (e) { console.error(e); }
        },

        async deleteAttachment(attachmentId) {
            if (!confirm('Удалить этот файл?')) return;
            try {
                await this.apiFetch(`/api/attachments/${attachmentId}`, { method: 'DELETE' });
                this.activeTask.attachments = this.activeTask.attachments.filter(a => a.id !== attachmentId);
                const idx = this.tasks.findIndex(t => t.id === this.activeTask.id);
                if (idx !== -1) this.tasks[idx].attachments = this.activeTask.attachments;
            } catch (e) { alert(e.message); }
        },

        handleCreateFileSelect(event) {
            this.createTaskPendingFiles = Array.from(event.target.files);
        },

        formatFileSize(bytes) {
            if (!bytes || bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        },

        isImageFile(filename) {
            if (!filename) return false;
            const ext = filename.split('.').pop().toLowerCase();
            return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext);
        },

        async submitComment() {
            if (!this.newCommentText.trim()) return;
            try {
                const comm = await this.apiFetch(`/api/tasks/${this.activeTask.id}/comments`, {
                    method: 'POST',
                    body: { content: this.newCommentText }
                });
                this.activeComments.push(comm);
                this.newCommentText = '';
                this.activeTask.comments_count = (this.activeTask.comments_count || 0) + 1;
                const idx = this.tasks.findIndex(t => t.id === this.activeTask.id);
                if (idx !== -1) this.tasks[idx].comments_count = this.activeTask.comments_count;
                this.refreshIcons();
            } catch (e) { alert(e.message); }
        },

        async inviteUserToChat(userId) {
            if (!userId) return;
            try {
                const comm = await this.apiFetch(`/api/tasks/${this.activeTask.id}/invite`, {
                    method: 'POST',
                    body: { user_id: parseInt(userId) }
                });
                this.activeComments.push(comm);
                this.activeTask.comments_count = (this.activeTask.comments_count || 0) + 1;
                
                // Refresh active task watchers
                const updatedTask = await this.apiFetch(`/api/tasks/${this.activeTask.id}`);
                this.activeTask = updatedTask;
                const idx = this.tasks.findIndex(t => t.id === this.activeTask.id);
                if (idx !== -1) this.tasks[idx] = updatedTask;

                this.refreshIcons();
            } catch (e) { alert(e.message); }
        },

        insertMention(username) {
            if (!this.newCommentText) this.newCommentText = '';
            if (!this.newCommentText.endsWith(' ') && this.newCommentText.length > 0) {
                this.newCommentText += ' ';
            }
            this.newCommentText += `@${username} `;
        },

        // Create Task / Bug Modal
        openCreateModal(defaultStatus = 'todo', taskType = 'task') {
            this.submittingTask = false;
            this.createTaskPendingFiles = [];
            this.createTaskForm = {
                title: '',
                description: '',
                status: defaultStatus,
                priority: taskType === 'bug' ? 'high' : 'medium',
                assignee_id: this.currentUser.id || null,
                due_date: '',
                tags: taskType === 'bug' ? 'Bug' : '',
                task_type: taskType,
                severity: 'major',
                steps_to_reproduce: '',
                watcher_ids: []
            };
            this.showCreateModal = true;
            this.refreshIcons();
        },

        isWatching(task) {
            if (!task || !task.watchers || !this.currentUser) return false;
            return task.watchers.some(w => w.id === this.currentUser.id);
        },

        async toggleMyWatcher(taskId) {
            try {
                const updated = await this.apiFetch(`/api/tasks/${taskId}/watchers/toggle`, { method: 'POST' });
                if (this.activeTask && this.activeTask.id === taskId) {
                    this.activeTask = updated;
                }
                const idx = this.tasks.findIndex(t => t.id === taskId);
                if (idx !== -1) this.tasks[idx] = updated;
                this.refreshIcons();
            } catch (e) { alert(e.message); }
        },

        openCreateBugModal() {
            this.openCreateModal('todo', 'bug');
        },

        async createTask() {
            if (this.submittingTask) return;
            this.submittingTask = true;
            try {
                const created = await this.apiFetch('/api/tasks', {
                    method: 'POST',
                    body: this.createTaskForm
                });

                // If user selected files during creation, upload batch now
                if (this.createTaskPendingFiles && this.createTaskPendingFiles.length) {
                    const formData = new FormData();
                    for (const file of this.createTaskPendingFiles) {
                        formData.append('files', file);
                    }
                    await fetch(`/api/tasks/${created.id}/attachments/batch`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${this.token}` },
                        body: formData
                    });
                }
                this.createTaskPendingFiles = [];
                this.showCreateModal = false;
                this.fetchTasks();
                this.fetchUserStats();
            } catch (e) {
                alert(e.message);
            } finally {
                this.submittingTask = false;
            }
        },

        // Formatting Utilities
        getInitials(name) {
            if (!name) return 'U';
            return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        },

        formatDate(dateStr) {
            if (!dateStr) return '';
            const d = new Date(dateStr);
            return d.toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
        },

        getTagsList(tagsStr) {
            if (!tagsStr) return [];
            return tagsStr.split(',').map(t => t.trim()).filter(Boolean);
        },

        isOverdue(dueDate, status) {
            if (!dueDate || status === 'done') return false;
            return new Date(dueDate) < new Date(new Date().toDateString());
        },

        getPriorityColor(priority) {
            switch (priority) {
                case 'urgent': return 'bg-red-500';
                case 'high': return 'bg-orange-500';
                case 'medium': return 'bg-amber-500';
                case 'low': return 'bg-slate-400';
                default: return 'bg-slate-400';
            }
        },

        getPriorityBadgeClass(priority) {
            switch (priority) {
                case 'urgent': return 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300 border border-red-200 dark:border-red-800';
                case 'high': return 'bg-orange-100 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300 border border-orange-200 dark:border-orange-800';
                case 'medium': return 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800';
                case 'low': return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600';
                default: return 'bg-slate-100 text-slate-700';
            }
        },

        getPriorityLabel(priority) {
            switch (priority) {
                case 'urgent': return 'Срочно';
                case 'high': return 'Высокий';
                case 'medium': return 'Средний';
                case 'low': return 'Низкий';
                default: return priority;
            }
        },

        getSeverityBadgeClass(severity) {
            switch (severity) {
                case 'critical': return 'bg-red-600 text-white font-bold shadow-xs';
                case 'major': return 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border border-red-200 dark:border-red-800';
                case 'minor': return 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800';
                case 'trivial': return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
                default: return 'bg-slate-100 text-slate-700';
            }
        },

        getSeverityLabel(severity) {
            switch (severity) {
                case 'critical': return 'Критический (Блокер)';
                case 'major': return 'Высокий приоритет';
                case 'minor': return 'Средний приоритет';
                case 'trivial': return 'Минорный';
                default: return severity || 'Не указана';
            }
        },

        getStatusBadgeClass(status) {
            switch (status) {
                case 'todo': return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
                case 'in_progress': return 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300';
                case 'in_review': return 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300';
                case 'on_hold': return 'bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300';
                case 'done': return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300';
                default: return 'bg-slate-100 text-slate-700';
            }
        },

        getStatusLabel(status) {
            switch (status) {
                case 'todo': return 'Новая';
                case 'in_progress': return 'В работе';
                case 'in_review': return 'На проверке';
                case 'on_hold': return 'Отложена';
                case 'done': return 'Завершена';
                default: return status;
            }
        },

        async saveActiveTask() {
            if (!this.activeTask || !this.activeTask.id) return;
            try {
                const updated = await this.apiFetch(`/api/tasks/${this.activeTask.id}`, {
                    method: 'PATCH',
                    body: {
                        title: this.activeTask.title,
                        description: this.activeTask.description,
                        status: this.activeTask.status,
                        priority: this.activeTask.priority,
                        assignee_id: this.activeTask.assignee_id,
                        due_date: this.activeTask.due_date,
                        severity: this.activeTask.severity,
                        steps_to_reproduce: this.activeTask.steps_to_reproduce
                    }
                });
                this.activeTask = updated;
                this.fetchTasks();
                this.fetchUserStats();
                this.showDetailModal = false;
            } catch (e) { alert(e.message); }
        },

        async updateActiveTaskStatus(newStatus) {
            if (!this.activeTask || !this.activeTask.id) return;
            this.activeTask.status = newStatus;
            await this.updateActiveTaskField('status', newStatus);
            if (newStatus === 'on_hold') {
                this.showDetailModal = false;
            }
        },

        closeAllModals() {
            this.userMenuOpen = false;
            this.notificationMenuOpen = false;
            this.showDetailModal = false;
            this.showUserProfileModal = false;
            this.showEditProfileModal = false;
            this.showAdminAddUserModal = false;
            this.showAdminEditUserModal = false;
            this.showCreateModal = false;
            this.showReopenModal = false;
            this.aiSummaryResult = '';
            this.activeMediaPreview = null;
        },

        async fetchNotifications() {
            try {
                this.notifications = await this.apiFetch('/api/notifications');
            } catch (e) { console.error(e); }
        },

        async markNotificationRead(id, taskId = null) {
            try {
                await this.apiFetch(`/api/notifications/${id}/read`, { method: 'POST' });
                const n = this.notifications.find(item => item.id === id);
                if (n) n.is_read = true;
                if (taskId) {
                    this.notificationMenuOpen = false;
                    this.openTaskDetail(taskId);
                }
            } catch (e) { console.error(e); }
        },

        async markAllNotificationsRead() {
            try {
                await this.apiFetch('/api/notifications/read-all', { method: 'POST' });
                (this.notifications || []).forEach(n => n.is_read = true);
            } catch (e) { console.error(e); }
        },

        get unreadNotificationsCount() {
            return (this.notifications || []).filter(n => !n.is_read).length;
        },

        // Subtask Methods
        async addSubtask() {
            if (!this.newSubtaskTitle.trim() || !this.activeTask.id) return;
            try {
                const sub = await this.apiFetch(`/api/tasks/${this.activeTask.id}/subtasks`, {
                    method: 'POST',
                    body: { title: this.newSubtaskTitle.trim() }
                });
                if (!this.activeTask.subtasks) this.activeTask.subtasks = [];
                this.activeTask.subtasks.push(sub);
                this.newSubtaskTitle = '';
                this.fetchTasks();
            } catch (e) { alert(e.message); }
        },

        async toggleSubtask(subtask) {
            try {
                const res = await this.apiFetch(`/api/subtasks/${subtask.id}`, {
                    method: 'PATCH',
                    body: { is_completed: subtask.is_completed }
                });
                if (res) {
                    subtask.is_completed = res.is_completed;
                }
                this.fetchTasks();
            } catch (e) {
                subtask.is_completed = !subtask.is_completed;
                alert(e.message);
            }
        },

        async deleteSubtask(subtaskId) {
            try {
                await this.apiFetch(`/api/subtasks/${subtaskId}`, { method: 'DELETE' });
                this.activeTask.subtasks = (this.activeTask.subtasks || []).filter(s => s.id !== subtaskId);
                this.fetchTasks();
            } catch (e) { alert(e.message); }
        },

        // AI Assistant Methods
        async aiGenerateSubtasks() {
            if (!this.activeTask.id) return;
            this.isGeneratingSubtasks = true;
            try {
                const newSubtasks = await this.apiFetch(`/api/tasks/${this.activeTask.id}/ai-generate-subtasks`, { method: 'POST' });
                this.activeTask.subtasks = newSubtasks;
            } catch (e) { alert(e.message); }
            finally { this.isGeneratingSubtasks = false; }
        },

        async aiSummarizeDiscussion() {
            if (!this.activeTask.id) return;
            this.isSummarizing = true;
            try {
                const res = await this.apiFetch(`/api/tasks/${this.activeTask.id}/ai-summarize`, { method: 'POST' });
                this.aiSummaryResult = res.summary;
            } catch (e) { alert(e.message); }
            finally { this.isSummarizing = false; }
        },

        openMediaPreview(filePath, filename) {
            this.activeMediaPreview = { url: filePath, filename: filename };
        },

        closeMediaPreview() {
            this.activeMediaPreview = null;
        },

        openUserProfile(userId) {
            this.closeAllModals();
            if (!userId) return;
            // The team list (/api/users) no longer includes payment_details —
            // it's private financial info and the API only returns it for the
            // logged-in user's own account. When viewing your own profile,
            // use currentUser (which does have it) instead of the stripped
            // entry from usersList.
            if (this.currentUser && userId === this.currentUser.id) {
                this.selectedUserProfile = this.currentUser;
                this.showUserProfileModal = true;
                this.$nextTick(() => this.refreshIcons());
                return;
            }
            const targetUser = this.usersList.find(u => u.id === userId);
            if (!targetUser) return;
            this.selectedUserProfile = targetUser;
            this.showUserProfileModal = true;
            this.$nextTick(() => {
                this.refreshIcons();
            });
        },

        get selectedUserTasks() {
            if (!this.selectedUserProfile) return [];
            const uid = this.selectedUserProfile.id;
            return this.tasks.filter(t => t.assignee_id === uid || t.creator_id === uid);
        },

        get selectedUserStats() {
            if (!this.selectedUserProfile) return { assigned: 0, completed: 0, created: 0, bugs: 0, rate: 0 };
            const uid = this.selectedUserProfile.id;
            const assigned = this.tasks.filter(t => t.assignee_id === uid);
            const completed = assigned.filter(t => t.status === 'done').length;
            const created = this.tasks.filter(t => t.creator_id === uid).length;
            const bugs = assigned.filter(t => t.task_type === 'bug' && t.status !== 'done').length;
            return {
                assigned: assigned.length,
                completed: completed,
                created: created,
                bugs: bugs,
                rate: assigned.length ? Math.round((completed / assigned.length) * 100) : 0
            };
        },

        openEditProfileModal() {
            this.closeAllModals();
            this.editProfileForm = {
                full_name: this.currentUser.full_name || '',
                email: this.currentUser.email || '',
                role: this.currentUser.role || '',
                role_description: this.currentUser.role_description || '',
                payment_details: this.currentUser.payment_details || '',
                avatar_color: this.currentUser.avatar_color || '#3b82f6'
            };
            this.showEditProfileModal = true;
            this.$nextTick(() => this.refreshIcons());
        },

        async saveProfile() {
            this.savingProfile = true;
            try {
                const updatedUser = await this.apiFetch('/api/users/me', {
                    method: 'PUT',
                    body: this.editProfileForm
                });
                this.currentUser = updatedUser;
                localStorage.setItem('tt_user', JSON.stringify(updatedUser));
                await this.fetchUsers();
                this.showEditProfileModal = false;
                if (this.selectedUserProfile && this.selectedUserProfile.id === updatedUser.id) {
                    this.selectedUserProfile = updatedUser;
                }
                alert('Профиль успешно сохранен!');
            } catch (e) {
                alert(e.message);
            } finally {
                this.savingProfile = false;
            }
        },

        async uploadUserAvatar(event) {
            const files = event.target.files;
            if (!files || !files.length) return;
            const formData = new FormData();
            formData.append('file', files[0]);
            try {
                const updatedUser = await this.apiFetch('/api/users/me/avatar', {
                    method: 'POST',
                    body: formData
                });
                this.currentUser = updatedUser;
                localStorage.setItem('tt_user', JSON.stringify(updatedUser));
                await this.fetchUsers();
                if (this.selectedUserProfile && this.selectedUserProfile.id === updatedUser.id) {
                    this.selectedUserProfile = updatedUser;
                }
            } catch (e) {
                alert(e.message);
            }
        },

        openAdminAddUserModal() {
            console.log("openAdminAddUserModal called");
            this.closeAllModals();
            this.adminAddUserForm = { username: '', full_name: '', password: '', email: '', role: 'Разработчик', role_description: '', payment_details: '' };
            this.showAdminAddUserModal = true;
            this.$nextTick(() => this.refreshIcons());
        },

        async adminAddUser() {
            try {
                const newUser = await this.apiFetch('/api/admin/users', {
                    method: 'POST',
                    body: this.adminAddUserForm
                });
                await this.fetchUsers();
                await this.fetchUserActivities();
                this.showAdminAddUserModal = false;
                alert(`Сотрудник ${newUser.full_name} (@${newUser.username}) успешно добавлен!`);
            } catch (e) {
                alert(e.message);
            }
        },

        openAdminEditUserModal(user) {
            console.log("openAdminEditUserModal called with:", user);
            let u = (typeof user === 'object' && user) ? user : this.usersList.find(x => String(x.id) === String(user));
            if (!u) {
                console.error("User not found in usersList:", user, this.usersList);
                alert("Ошибка: Пользователь не найден.");
                return;
            }
            this.closeAllModals();
            this.editingUserObj = u;
            this.adminEditUserForm = {
                username: u.username || '',
                full_name: u.full_name || '',
                email: u.email || '',
                password: '',
                role: u.role || 'Разработчик',
                role_description: u.role_description || '',
                payment_details: u.payment_details || '',
                avatar_color: u.avatar_color || '#3b82f6'
            };
            this.showAdminEditUserModal = true;
            this.$nextTick(() => this.refreshIcons());
        },

        async adminUpdateUser() {
            if (!this.editingUserObj) return;
            try {
                const updatedUser = await this.apiFetch(`/api/admin/users/${this.editingUserObj.id}`, {
                    method: 'PUT',
                    body: this.adminEditUserForm
                });
                await this.fetchUsers();
                await this.fetchUserActivities();
                if (this.currentUser.id === updatedUser.id) {
                    this.currentUser = updatedUser;
                    localStorage.setItem('tt_user', JSON.stringify(updatedUser));
                }
                this.showAdminEditUserModal = false;
                alert(`Профиль сотрудника ${updatedUser.full_name} обновлен!`);
            } catch (e) {
                alert(e.message);
            }
        },

        async adminDeleteUser(user) {
            let u = (typeof user === 'object' && user) ? user : this.usersList.find(x => String(x.id) === String(user));
            if (!u) return;
            if (!confirm(`Вы действительно хотите удалить сотрудника ${u.full_name} (@${u.username})?`)) return;
            try {
                await this.apiFetch(`/api/admin/users/${u.id}`, { method: 'DELETE' });
                await this.fetchUsers();
                await this.fetchUserActivities();
                await this.fetchTasks();
                alert(`Сотрудник ${u.full_name} удален из системы.`);
            } catch (e) {
                alert(e.message);
            }
        }
    };
}

window.taskTrackerApp = taskTrackerApp;

if (window.Alpine) {
    Alpine.data('taskTrackerApp', taskTrackerApp);
}
document.addEventListener('alpine:init', () => {
    Alpine.data('taskTrackerApp', taskTrackerApp);
});
