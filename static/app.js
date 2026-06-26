document.addEventListener('DOMContentLoaded', () => {
    // Current active views and elements
    const navItems = document.querySelectorAll('.nav-item');
    const tabViews = document.querySelectorAll('.tab-view');
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');
    
    // Stats elements
    const statTotal = document.getElementById('stat-total');
    const statWhatsapp = document.getElementById('stat-whatsapp');
    const statEmail = document.getElementById('stat-email');
    const statSpeed = document.getElementById('stat-speed');
    
    // Status elements
    const globalStatusBadge = document.getElementById('global-status-badge');
    const globalStatusText = document.getElementById('global-status-text');
    const statusWhatsappBrowser = document.getElementById('status-whatsapp-browser');
    const statusGmailBrowser = document.getElementById('status-gmail-browser');
    
    // Session elements
    const sessionStatusWa = document.getElementById('session-status-wa');
    const sessionStatusGm = document.getElementById('session-status-gm');
    
    // Progress elements
    const progressBar = document.getElementById('progress-bar');
    const progressPercent = document.getElementById('progress-percent');
    const progressRatio = document.getElementById('progress-ratio');
    const activeContactPanel = document.getElementById('active-contact-panel');
    const currentName = document.getElementById('current-name');
    const currentPhone = document.getElementById('current-phone');
    const currentEmail = document.getElementById('current-email');
    
    // Control Buttons
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const btnDispatchLaunch = document.getElementById('btn-dispatch-launch');
    const messagingMode = document.getElementById('messaging-mode');
    
    // Session Buttons
    const btnLoginWhatsapp = document.getElementById('btn-login-whatsapp');
    const btnLoginGmail = document.getElementById('btn-login-gmail');
    
    // Templates
    const txtWaTemplate = document.getElementById('txt-wa-template');
    const txtEmailTemplate = document.getElementById('txt-email-template');
    const btnSaveTemplates = document.getElementById('btn-save-templates');
    
    // Settings Form
    const settingsForm = document.getElementById('settings-form');
    const whatsappSenderNum = document.getElementById('whatsapp-sender-num');
    const gmailSenderId = document.getElementById('gmail-sender-id');
    const toggleAttachment = document.getElementById('toggle-attachment');
    const toggleMl = document.getElementById('toggle-ml');
    const minDelay = document.getElementById('min-delay');
    const maxDelay = document.getElementById('max-delay');
    const btnSaveSettings = document.getElementById('btn-save-settings');
    const activePdfName = document.getElementById('active-pdf-name');
    
    // Terminal Log
    const logTerminal = document.getElementById('log-terminal');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    
    // File upload elements
    const dropZoneContacts = document.getElementById('drop-zone-contacts');
    const inputContactsFile = document.getElementById('input-contacts-file');
    const dropZoneAttachment = document.getElementById('drop-zone-attachment');
    const inputAttachmentFile = document.getElementById('input-attachment-file');

    // Page state variables
    let isSendingState = false;
    let loggedLogs = [];

    // Contacts state
    let allContacts = [];
    let contactsColumns = [];



    // Dashboard confirmation elements
    const dashboardLoginConfirm      = document.getElementById('dashboard-login-confirm');
    const dashboardLoginConfirmLabel = document.getElementById('dashboard-login-confirm-label');
    const btnDashboardConfirmWhatsapp = document.getElementById('btn-dashboard-confirm-whatsapp');
    const btnDashboardConfirmGmail    = document.getElementById('btn-dashboard-confirm-gmail');

    // Logs confirmation elements
    const logsLoginConfirm      = document.getElementById('logs-login-confirm');
    const logsLoginConfirmLabel = document.getElementById('logs-login-confirm-label');
    const btnLogsConfirmWhatsapp = document.getElementById('btn-logs-confirm-whatsapp');
    const btnLogsConfirmGmail    = document.getElementById('btn-logs-confirm-gmail');

    // --- VIEW NAVIGATION CONTROLLER ---
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('href').substring(1);
            
            // Toggle active menu class
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            // Toggle active content tab view
            tabViews.forEach(view => view.classList.remove('active-view'));
            document.getElementById(`view-${targetId}`).classList.add('active-view');
            
            // Update page headers dynamically
            const titleMap = {
                'dashboard': ['Dashboard Overview', 'Real-time stats and control center'],
                'sessions': ['Browser Login Manager', 'Authenticate WhatsApp Web and Gmail sessions'],
                'contacts': ['Contact List', 'View, search and manage all contacts loaded from Excel'],
                'templates': ['Configure Message Templates', 'Customize text campaigns for WhatsApp and Gmail'],
                'settings': ['Campaign Configuration', 'Adjust system parameters, uploads, and attachment rules'],
                'logs': ['Terminal Output Stream', 'Monitor Selenium automation outputs in real-time']
            };
            
            pageTitle.innerText = titleMap[targetId][0];
            pageSubtitle.innerText = titleMap[targetId][1];

            // Auto-load contacts when navigating to that tab
            if (targetId === 'contacts') {
                loadContacts();
            }
        });
    });

    // --- POLLING CONTROLLER ---
    // Fetch Status details from API
    const fetchStatus = async () => {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            isSendingState = data.is_sending;
            
            // Update System Status badge
            if (isSendingState) {
                globalStatusBadge.className = 'status-indicator sending';
                globalStatusText.innerText = 'Sending Batch...';
                
                // Toggle dispatch buttons state
                btnStart.disabled = true;
                btnStop.disabled = false;
                btnDispatchLaunch.disabled = true;
                btnDispatchLaunch.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Dispatching...';
            } else {
                globalStatusBadge.className = 'status-indicator idle';
                globalStatusText.innerText = 'System Idle';
                
                btnStart.disabled = false;
                btnStop.disabled = true;
                btnDispatchLaunch.disabled = false;
                btnDispatchLaunch.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Launch Sending Process';
            }
            
            // Update Browser Connected status
            updateBrowserStatusBadge(statusWhatsappBrowser, sessionStatusWa, data.whatsapp_browser_active);
            updateBrowserStatusBadge(statusGmailBrowser, sessionStatusGm, data.gmail_browser_active);
            
            // Update Progress Details
            const progress = data.progress;
            const currentCount = progress.current;
            const totalCount = progress.total;
            const percentage = totalCount > 0 ? Math.round((currentCount / totalCount) * 100) : 0;
            
            progressBar.style.width = `${percentage}%`;
            progressPercent.innerText = `${percentage}%`;
            progressRatio.innerText = `${currentCount} / ${totalCount} processed`;
            
            // Update stats cards
            statTotal.innerText = totalCount;
            statWhatsapp.innerText = progress.whatsapp_success;
            statEmail.innerText = progress.email_success;
            
            // Update active contact dashboard details
            if (isSendingState && progress.name) {
                activeContactPanel.style.display = 'block';
                currentName.innerText = progress.name || 'Unknown';
                currentPhone.innerText = progress.phone || 'None';
                currentEmail.innerText = progress.email || 'None';
            } else if (!isSendingState) {
                // Keep info displayed if completed or hide it
            }
            
            // Update login confirm banner visibility
            if (data.login_status) {
                updateLoginConfirmBanner(data.login_status);
            }
            
        } catch (error) {
            console.error('Error fetching status:', error);
        }
    };
    
    // Status badge utility
    const updateBrowserStatusBadge = (badgeElem, textElem, isActive) => {
        if (isActive) {
            badgeElem.className = 'badge badge-success';
            badgeElem.innerHTML = '<i class="fa-solid fa-check"></i> Connected';
            if (textElem) {
                textElem.className = 'session-status online';
                textElem.innerText = 'Connected / Ready';
            }
        } else {
            badgeElem.className = 'badge badge-danger';
            badgeElem.innerHTML = '<i class="fa-solid fa-times"></i> Offline';
            if (textElem) {
                textElem.className = 'session-status offline';
                textElem.innerText = 'Disconnected';
            }
        }
    };

    // --- LOGIN CONFIRM BANNER CONTROLLER ---
    const updateLoginConfirmBanner = (loginStatus) => {
        const waWaiting = loginStatus.whatsapp === 'waiting' || loginStatus.whatsapp === 'confirmed';
        const gmWaiting = loginStatus.gmail === 'waiting'    || loginStatus.gmail === 'confirmed';
        const anyWaiting = waWaiting || gmWaiting;

        // Show or hide the banners across pages
        const displayStyle = anyWaiting ? 'block' : 'none';
        if (dashboardLoginConfirm) dashboardLoginConfirm.style.display = displayStyle;
        if (logsLoginConfirm) logsLoginConfirm.style.display = displayStyle;

        if (!anyWaiting) {
            return;
        }

        // Auto-navigate to Logs tab only if user is not on Dashboard or Logs already
        const activeView = document.querySelector('.tab-view.active-view');
        const activeId = activeView ? activeView.id : '';
        if (activeId !== 'view-dashboard' && activeId !== 'view-logs') {
            const logsNavBtn = document.getElementById('nav-logs');
            const logsView   = document.getElementById('view-logs');
            if (logsView && !logsView.classList.contains('active-view')) {
                logsNavBtn && logsNavBtn.click();
            }
        }

        let labelText = '';
        if (loginStatus.whatsapp === 'confirmed' || loginStatus.gmail === 'confirmed') {
            labelText = '✅ Login confirmed — loading session, please wait...';
        } else {
            const parts = [];
            if (waWaiting) parts.push('WhatsApp');
            if (gmWaiting) parts.push('Gmail');
            labelText = `🔐 Chrome is open — log in to ${parts.join(' & ')} in the Chrome window, then click the Confirm button.`;
        }

        if (dashboardLoginConfirmLabel) dashboardLoginConfirmLabel.innerText = labelText;
        if (logsLoginConfirmLabel) logsLoginConfirmLabel.innerText = labelText;

        // Show/hide individual buttons
        const waBtnDisplay = loginStatus.whatsapp === 'waiting' ? 'inline-flex' : 'none';
        if (btnDashboardConfirmWhatsapp) btnDashboardConfirmWhatsapp.style.display = waBtnDisplay;
        if (btnLogsConfirmWhatsapp) btnLogsConfirmWhatsapp.style.display = waBtnDisplay;

        const gmBtnDisplay = loginStatus.gmail === 'waiting' ? 'inline-flex' : 'none';
        if (btnDashboardConfirmGmail) btnDashboardConfirmGmail.style.display = gmBtnDisplay;
        if (btnLogsConfirmGmail) btnLogsConfirmGmail.style.display = gmBtnDisplay;
    };

    const confirmLogin = async (service, btnElem) => {
        // Disable all confirm buttons for this service across pages
        const allButtonsForService = document.querySelectorAll(`[id$="confirm-${service}"]`);
        allButtonsForService.forEach(btn => {
            btn.disabled = true;
            btn.dataset.originalHtml = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Confirming...';
        });

        try {
            const response = await fetch(`/api/confirm-login/${service}`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                allButtonsForService.forEach(btn => {
                    btn.innerHTML = '<i class="fa-solid fa-check"></i> Confirmed!';
                });
            } else {
                alert(`Could not confirm login: ${result.error}`);
                allButtonsForService.forEach(btn => {
                    btn.disabled = false;
                    btn.innerHTML = btn.dataset.originalHtml || (service === 'whatsapp' ? '<i class="fa-brands fa-whatsapp"></i> Confirm WhatsApp Login' : '<i class="fa-solid fa-envelope"></i> Confirm Gmail Login');
                });
            }
        } catch (err) {
            alert(`Network error: ${err.message}`);
            allButtonsForService.forEach(btn => {
                btn.disabled = false;
                btn.innerHTML = btn.dataset.originalHtml || (service === 'whatsapp' ? '<i class="fa-brands fa-whatsapp"></i> Confirm WhatsApp Login' : '<i class="fa-solid fa-envelope"></i> Confirm Gmail Login');
            });
        }
    };



    if (btnDashboardConfirmWhatsapp) {
        btnDashboardConfirmWhatsapp.addEventListener('click', () => confirmLogin('whatsapp', btnDashboardConfirmWhatsapp));
    }
    if (btnDashboardConfirmGmail) {
        btnDashboardConfirmGmail.addEventListener('click', () => confirmLogin('gmail', btnDashboardConfirmGmail));
    }
    if (btnLogsConfirmWhatsapp) {
        btnLogsConfirmWhatsapp.addEventListener('click', () => confirmLogin('whatsapp', btnLogsConfirmWhatsapp));
    }
    if (btnLogsConfirmGmail) {
        btnLogsConfirmGmail.addEventListener('click', () => confirmLogin('gmail', btnLogsConfirmGmail));
    }

    // Fetch logs from API
    const fetchLogs = async () => {
        try {
            const response = await fetch('/api/logs');
            const data = await response.json();
            
            const newLogs = data.logs || [];
            
            // Check if there are new logs to draw
            if (newLogs.length > loggedLogs.length) {
                const logsToAppend = newLogs.slice(loggedLogs.length);
                
                logsToAppend.forEach(line => {
                    const logElem = document.createElement('div');
                    logElem.className = 'log-line';
                    
                    // Style special system lines
                    if (line.includes('❌') || line.toLowerCase().includes('error')) {
                        logElem.classList.add('error');
                    } else if (line.includes('⚠️') || line.toLowerCase().includes('warning')) {
                        logElem.classList.add('warning');
                    } else if (line.includes('✅') || line.includes('[SYSTEM]')) {
                        logElem.classList.add('system');
                    }
                    
                    logElem.innerText = line;
                    logTerminal.appendChild(logElem);
                });
                
                // Keep terminal scrolled to bottom
                logTerminal.scrollTop = logTerminal.scrollHeight;
                loggedLogs = newLogs;
            }
        } catch (error) {
            console.error('Error fetching logs:', error);
        }
    };

    // --- CONFIG & DATA CONTROLLER ---
    // Load Settings on initial page load
    const loadSettings = async () => {
        try {
            const response = await fetch('/api/settings');
            const data = await response.json();
            
            const config = data.config || {};
            
            // Map settings values to form elements
            whatsappSenderNum.value = config.whatsapp_sender || '';
            gmailSenderId.value = config.gmail_sender || '';
            toggleAttachment.checked = config.send_with_attachment !== false;
            toggleMl.checked = config.use_ml_optimization !== false;
            minDelay.value = config.min_wait_seconds || 60;
            maxDelay.value = config.max_wait_seconds || 60;
            
            activePdfName.innerText = config.attachment_path || 'None';
            
            // Set message templates textareas
            txtWaTemplate.value = data.whatsapp_template || '';
            txtEmailTemplate.value = data.email_template || '';
            
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    };

    // Save Template modifications
    btnSaveTemplates.addEventListener('click', async () => {
        try {
            btnSaveTemplates.disabled = true;
            btnSaveTemplates.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
            
            // Read templates text from textareas
            const payload = {
                'whatsapp_template': txtWaTemplate.value,
                'email_template': txtEmailTemplate.value
            };
            
            // Reuse post settings endpoint to save templates
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            if (result.success) {
                alert('Templates updated successfully!');
            } else {
                alert(`Error saving templates: ${result.error}`);
            }
        } catch (error) {
            alert(`Error saving templates: ${error.message}`);
        } finally {
            btnSaveTemplates.disabled = false;
            btnSaveTemplates.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Message Templates';
        }
    });

    // Save Settings panel configuration
    btnSaveSettings.addEventListener('click', async () => {
        try {
            btnSaveSettings.disabled = true;
            btnSaveSettings.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Applying...';
            
            const payload = {
                'whatsapp_sender': whatsappSenderNum.value,
                'gmail_sender': gmailSenderId.value,
                'send_with_attachment': toggleAttachment.checked,
                'use_ml_optimization': toggleMl.checked,
                'min_wait_seconds': parseInt(minDelay.value) || 60,
                'max_wait_seconds': parseInt(maxDelay.value) || 60
            };
            
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            if (result.success) {
                alert('Settings applied successfully!');
                await loadSettings(); // Reload settings display
            } else {
                alert(`Error updating settings: ${result.error}`);
            }
        } catch (error) {
            alert(`Error applying settings: ${error.message}`);
        } finally {
            btnSaveSettings.disabled = false;
            btnSaveSettings.innerHTML = '<i class="fa-solid fa-check"></i> Apply Settings';
        }
    });

    // --- CHROMEDRIVER / LOGIN ACTIONS ---
    btnLoginWhatsapp.addEventListener('click', () => triggerLogin('whatsapp', btnLoginWhatsapp));
    btnLoginGmail.addEventListener('click', () => triggerLogin('gmail', btnLoginGmail));

    const triggerLogin = async (service, buttonElem) => {
        try {
            buttonElem.disabled = true;
            const origHTML = buttonElem.innerHTML;
            buttonElem.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Launching Chrome...';
            
            const response = await fetch(`/api/login/${service}`, { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                alert(`Chrome launched successfully for ${service}! Follow the steps in the browser window to log in.`);
            } else {
                alert(`Error launching driver: ${result.error}`);
            }
            
            buttonElem.disabled = false;
            buttonElem.innerHTML = origHTML;
        } catch (error) {
            alert(`Network error launching Chrome: ${error.message}`);
            buttonElem.disabled = false;
        }
    };

    // --- DISPATCH ACTIONS ---
    const startDispatch = async (choiceVal) => {
        try {
            const response = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ choice: choiceVal })
            });
            const result = await response.json();
            
            if (result.success) {
                // Switch view to logs automatically so user can watch the progress
                document.getElementById('nav-logs').click();
            } else {
                alert(`Failed to start: ${result.error}`);
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    };
    
    // Bind starts
    btnStart.addEventListener('click', () => startDispatch(messagingMode.value));
    btnDispatchLaunch.addEventListener('click', () => startDispatch(messagingMode.value));
    
    // Bind stop
    btnStop.addEventListener('click', async () => {
        try {
            btnStop.disabled = true;
            btnStop.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Stopping...';
            const response = await fetch('/api/stop', { method: 'POST' });
            const result = await response.json();
            if (!result.success) {
                alert(`Error stopping: ${result.error}`);
            }
        } catch (error) {
            alert(`Error stopping: ${error.message}`);
        } finally {
            btnStop.disabled = false;
            btnStop.innerHTML = '<i class="fa-solid fa-stop"></i> Stop';
        }
    });
    
    // Clear console log
    btnClearLogs.addEventListener('click', () => {
        logTerminal.innerHTML = '<div class="log-line system">[SYSTEM] Console logger cleared. Output logs will resume...</div>';
        loggedLogs = [];
    });

    // --- FILE UPLOADER DRAG & DROP CONTROLS ---
    const handleDragOver = (e) => {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    };
    
    const handleDragLeave = (e) => {
        e.currentTarget.classList.remove('dragover');
    };

    // Drag-over drop zone handlers
    [dropZoneContacts, dropZoneAttachment].forEach(zone => {
        zone.addEventListener('dragover', handleDragOver);
        zone.addEventListener('dragleave', handleDragLeave);
    });

    // Contact drop/click upload
    dropZoneContacts.addEventListener('click', () => inputContactsFile.click());
    inputContactsFile.addEventListener('change', (e) => handleFileUpload(e.target.files[0], 'contacts'));
    dropZoneContacts.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZoneContacts.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0], 'contacts');
        }
    });

    // Attachment drop/click upload
    dropZoneAttachment.addEventListener('click', () => inputAttachmentFile.click());
    inputAttachmentFile.addEventListener('change', (e) => handleFileUpload(e.target.files[0], 'attachment'));
    dropZoneAttachment.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZoneAttachment.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0], 'attachment');
        }
    });

    // File Uploader handler
    const handleFileUpload = async (file, type) => {
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        const dropZone = type === 'contacts' ? dropZoneContacts : dropZoneAttachment;
        const origHTML = dropZone.innerHTML;
        dropZone.innerHTML = `<i class="fa-solid fa-spinner fa-spin drop-icon"></i><p>Uploading <strong>${file.name}</strong>...</p>`;
        
        try {
            const url = type === 'contacts' ? '/api/upload/contacts' : '/api/upload/attachment';
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.success) {
                alert(`Upload Successful: ${file.name}`);
                if (type === 'attachment') {
                    activePdfName.innerText = file.name;
                }
            } else {
                alert(`Upload Failed: ${result.error}`);
            }
        } catch (error) {
            alert(`Network error uploading file: ${error.message}`);
        } finally {
            dropZone.innerHTML = origHTML;
        }
    };

    // --- CONTACTS TABLE CONTROLLER ---
    const contactsSearch = document.getElementById('contacts-search');
    const btnRefreshContacts = document.getElementById('btn-refresh-contacts');
    const contactsCountBadge = document.getElementById('contacts-count-badge');
    const contactsHeaderMeta = document.getElementById('contacts-header-meta');
    const contactsLoading = document.getElementById('contacts-loading');
    const contactsTable = document.getElementById('contacts-table');
    const contactsThead = document.getElementById('contacts-thead');
    const contactsTbody = document.getElementById('contacts-tbody');
    const contactsEmpty = document.getElementById('contacts-empty');

    const loadContacts = async () => {
        // Show loading state
        contactsLoading.style.display = 'flex';
        contactsTable.style.display = 'none';
        contactsEmpty.style.display = 'none';
        contactsHeaderMeta.innerText = 'Loading...';
        contactsCountBadge.innerText = '…';

        try {
            const response = await fetch('/api/contacts');
            const data = await response.json();

            if (data.error && data.total === 0) {
                contactsLoading.style.display = 'none';
                contactsEmpty.style.display = 'flex';
                contactsHeaderMeta.innerText = data.error;
                contactsCountBadge.innerText = '0 contacts';
                return;
            }

            allContacts = data.contacts || [];
            contactsColumns = data.columns || [];

            renderContactsTable(allContacts);
        } catch (err) {
            contactsLoading.style.display = 'none';
            contactsEmpty.style.display = 'flex';
            contactsHeaderMeta.innerText = 'Failed to load contacts.';
            contactsCountBadge.innerText = '0 contacts';
        }
    };

    const renderContactsTable = (contacts) => {
        contactsLoading.style.display = 'none';

        if (!contacts || contacts.length === 0) {
            contactsTable.style.display = 'none';
            contactsEmpty.style.display = 'flex';
            contactsCountBadge.innerText = '0 contacts';
            contactsHeaderMeta.innerText = 'No contacts match your search.';
            return;
        }

        contactsEmpty.style.display = 'none';
        contactsTable.style.display = 'table';

        const displayCount = contacts.length;
        const totalCount = allContacts.length;
        contactsCountBadge.innerText = `${displayCount} contact${displayCount !== 1 ? 's' : ''}`;
        contactsHeaderMeta.innerText = displayCount === totalCount
            ? `${totalCount} total records`
            : `Showing ${displayCount} of ${totalCount} records`;

        // Build thead
        contactsThead.innerHTML = '';
        const headerRow = document.createElement('tr');
        const thIdx = document.createElement('th');
        thIdx.innerText = '#';
        thIdx.className = 'col-index';
        headerRow.appendChild(thIdx);

        contactsColumns.forEach(col => {
            const th = document.createElement('th');
            th.innerText = col;
            headerRow.appendChild(th);
        });

        const thActions = document.createElement('th');
        thActions.innerText = 'Actions';
        thActions.className = 'col-actions';
        headerRow.appendChild(thActions);
        contactsThead.appendChild(headerRow);

        // Build tbody
        contactsTbody.innerHTML = '';
        contacts.forEach((row, displayIdx) => {
            // Find the real index in allContacts
            const realIdx = allContacts.indexOf(row);

            const tr = document.createElement('tr');
            tr.className = 'contact-row';
            tr.setAttribute('data-real-index', realIdx);

            const tdIdx = document.createElement('td');
            tdIdx.className = 'col-index';
            tdIdx.innerText = realIdx + 1;
            tr.appendChild(tdIdx);

            contactsColumns.forEach(col => {
                const td = document.createElement('td');
                const val = row[col] !== undefined ? String(row[col]) : '';
                td.innerText = val;

                // Add semantic colour chips for phone/email columns
                const colLower = col.toLowerCase();
                if (colLower.includes('email') && val.includes('@')) {
                    td.innerHTML = `<span class="contact-chip chip-email"><i class="fa-solid fa-envelope"></i> ${val}</span>`;
                } else if ((colLower.includes('phone') || colLower.includes('mobile') || colLower.includes('number')) && val) {
                    td.innerHTML = `<span class="contact-chip chip-phone"><i class="fa-solid fa-phone"></i> ${val}</span>`;
                }

                tr.appendChild(td);
            });

            const tdAction = document.createElement('td');
            tdAction.className = 'col-actions';
            const delBtn = document.createElement('button');
            delBtn.className = 'btn-delete-contact';
            delBtn.title = 'Delete this contact';
            delBtn.innerHTML = '<i class="fa-solid fa-trash-can"></i>';
            delBtn.addEventListener('click', () => deleteContact(realIdx, tr));
            tdAction.appendChild(delBtn);
            tr.appendChild(tdAction);

            contactsTbody.appendChild(tr);
        });
    };

    const deleteContact = async (realIdx, rowElem) => {
        if (!confirm(`Delete contact #${realIdx + 1}? This will permanently remove them from contacts.xlsx.`)) return;

        rowElem.style.opacity = '0.4';
        rowElem.style.pointerEvents = 'none';

        try {
            const response = await fetch(`/api/contacts/${realIdx}`, { method: 'DELETE' });
            const result = await response.json();

            if (result.success) {
                // Remove from local state and re-render
                allContacts.splice(realIdx, 1);
                // Update row indices after removal
                applyContactsSearch();
            } else {
                alert(`Failed to delete: ${result.error}`);
                rowElem.style.opacity = '1';
                rowElem.style.pointerEvents = '';
            }
        } catch (err) {
            alert(`Network error: ${err.message}`);
            rowElem.style.opacity = '1';
            rowElem.style.pointerEvents = '';
        }
    };

    const applyContactsSearch = () => {
        const query = (contactsSearch ? contactsSearch.value : '').toLowerCase().trim();
        if (!query) {
            renderContactsTable(allContacts);
            return;
        }
        const filtered = allContacts.filter(row => {
            return contactsColumns.some(col => {
                const val = row[col] !== undefined ? String(row[col]).toLowerCase() : '';
                return val.includes(query);
            });
        });
        renderContactsTable(filtered);
    };

    if (contactsSearch) {
        contactsSearch.addEventListener('input', applyContactsSearch);
    }

    if (btnRefreshContacts) {
        btnRefreshContacts.addEventListener('click', () => {
            if (contactsSearch) contactsSearch.value = '';
            loadContacts();
        });
    }

    // --- INITIALIZATION CAMPAIGN ---
    loadSettings();
    
    // Status polling intervals
    setInterval(fetchStatus, 1000);
    setInterval(fetchLogs, 1000);
});
