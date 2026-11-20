// Cloud Clipboard — shared across devices
// Polls /api/clipboard every 5s; never overwrites unsaved local edits.

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const clipboardText = document.getElementById('clipboardText');
    const charCount = document.getElementById('charCount');
    const wordCount = document.getElementById('wordCount');
    const uploadBtn = document.getElementById('uploadBtn');
    const fetchLatestBtn = document.getElementById('fetchLatestBtn');
    const copyClipboardBtn = document.getElementById('copyClipboardBtn');
    const clearClipboardBtn = document.getElementById('clearClipboardBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const updatedStamp = document.getElementById('updatedStamp');
    const syncBadge = document.getElementById('syncStatus');
    const syncStatusText = document.getElementById('syncStatusText');
    const statusUpdated = document.getElementById('statusUpdated');
    const statusChars = document.getElementById('statusChars');
    const statusWords = document.getElementById('statusWords');
    const statusSize = document.getElementById('statusSize');
    const stateBadge = document.getElementById('stateBadge');
    const themeToggle = document.getElementById('themeToggle');
    const toastContainer = document.getElementById('toastContainer');

    const API = '/api/clipboard';
    const POLL_MS = 5000;

    let currentText = '';   // last known cloud content
    let uploading = false;

    // --- Helper Functions ---
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        let iconName = 'info';
        if (type === 'success') iconName = 'check_circle';
        if (type === 'error') iconName = 'error';

        toast.innerHTML = `
            <span class="material-symbols-outlined">${iconName}</span>
            <span>${escapeHtml(message)}</span>
        `;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function countWords(text) {
        const trimmed = (text || '').trim();
        return trimmed ? trimmed.split(/\s+/).length : 0;
    }

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function formatTimestamp(isoString) {
        if (!isoString) return '';
        return new Date(isoString).toLocaleString();
    }

    function updateStats() {
        const text = clipboardText.value || '';
        charCount.textContent = `${text.length.toLocaleString()} characters`;
        wordCount.textContent = `${countWords(text).toLocaleString()} words`;
    }

    // Refresh the status panel + card header from cloud state
    function renderMeta(updatedAt, text) {
        updatedStamp.textContent = updatedAt ? `Updated ${formatTimestamp(updatedAt)}` : '';
        statusUpdated.textContent = updatedAt ? formatTimestamp(updatedAt) : '—';
        statusChars.textContent = text.length.toLocaleString();
        statusWords.textContent = countWords(text).toLocaleString();
        statusSize.textContent = formatBytes(new Blob([text]).size);
        stateBadge.textContent = text ? 'SHARED' : 'EMPTY';
    }

    function setSync(ok) {
        syncBadge.classList.toggle('offline', !ok);
        syncStatusText.textContent = ok ? 'Connected' : 'Offline';
    }

    // --- API Interactions ---

    // Fetch cloud clipboard. force=true overwrites the editor even with local
    // edits; otherwise the editor is only updated when it has no unsaved edits
    // and is not focused, so live sync never clobbers what you're typing.
    async function fetchClipboard(force = false, silent = false) {
        try {
            const response = await fetch(API);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            const remote = typeof data.text === 'string' ? data.text : '';
            const hasEdits = clipboardText.value !== currentText;
            const focused = document.activeElement === clipboardText;

            if (remote !== currentText || force) {
                if (force || (!hasEdits && !focused)) {
                    clipboardText.value = remote;
                    updateStats();
                }
                currentText = remote;
                renderMeta(data.updated_at, remote);
            }
            setSync(true);
            return true;
        } catch (error) {
            console.error('Error reading clipboard:', error);
            if (!silent) setSync(false);
            return false;
        }
    }

    async function updateClipboard() {
        if (uploading) return;
        uploading = true;
        const original = uploadBtn.innerHTML;
        uploadBtn.disabled = true;
        uploadBtn.innerHTML =
            '<span class="material-symbols-outlined" style="font-size:16px">cloud_sync</span> Uploading&hellip;';
        try {
            const response = await fetch(API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: clipboardText.value })
            });
            if (!response.ok) {
                const detail = (await response.json().catch(() => ({}))).detail;
                const msg = response.status === 422 && detail
                    ? 'Upload rejected: content too large (1,000,000 characters max).'
                    : `Upload failed (HTTP ${response.status}).`;
                throw new Error(msg);
            }
            const data = await response.json();
            currentText = data.text || '';
            renderMeta(data.updated_at, currentText);
            showToast('Cloud clipboard updated!', 'success');
        } catch (error) {
            if (error.message === 'Failed to fetch') setSync(false);
            showToast(error.message, 'error');
        } finally {
            uploading = false;
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = original;
        }
    }

    async function clearClipboard() {
        if (currentText === '' && clipboardText.value === '') {
            showToast('Nothing to clear!', 'info');
            return;
        }
        if (!confirm('Clear the shared clipboard? This wipes it for everyone.')) return;
        try {
            const response = await fetch(API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: '' })
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            currentText = data.text || '';
            clipboardText.value = '';
            updateStats();
            renderMeta(data.updated_at, currentText);
            showToast('Clipboard cleared!', 'info');
        } catch (error) {
            if (error.message === 'Failed to fetch') setSync(false);
            showToast('Failed to clear clipboard.', 'error');
        }
    }

    // Copy to local device clipboard (with fallback for non-secure contexts)
    async function copyToLocalClipboard(text) {
        if (!text) {
            showToast('Nothing to copy!', 'info');
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            showToast('Copied to device clipboard!', 'success');
        } catch (err) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.select();
            let ok = false;
            try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
            document.body.removeChild(textArea);
            if (ok) showToast('Copied to device clipboard!', 'success');
            else showToast('Copy failed — select the text manually.', 'error');
        }
    }

    async function handleManualFetch() {
        const ok = await fetchClipboard(true);
        showToast(ok ? 'Fetched latest cloud clipboard!' : 'Could not reach the server.', ok ? 'info' : 'error');
    }

    // --- Theme Toggle Management ---
    function applyTheme(theme) {
        document.body.setAttribute('data-theme', theme === 'pastel' ? 'pastel' : 'magenta');
        if (themeToggle) themeToggle.checked = theme === 'pastel';
        try { localStorage.setItem('cloud_clipboard_theme', theme === 'pastel' ? 'pastel' : 'magenta'); } catch (e) { /* private mode */ }
    }

    if (themeToggle) {
        themeToggle.addEventListener('change', () => applyTheme(themeToggle.checked ? 'pastel' : 'magenta'));
    }

    // --- Event Listeners ---
    clipboardText.addEventListener('input', updateStats);
    uploadBtn.addEventListener('click', updateClipboard);
    fetchLatestBtn.addEventListener('click', handleManualFetch);
    refreshBtn.addEventListener('click', handleManualFetch);
    copyClipboardBtn.addEventListener('click', () => copyToLocalClipboard(clipboardText.value));
    clearClipboardBtn.addEventListener('click', clearClipboard);

    // --- Initial Startup Sequence ---
    let savedTheme = 'magenta';
    try { savedTheme = localStorage.getItem('cloud_clipboard_theme') || 'magenta'; } catch (e) { /* private mode */ }
    applyTheme(savedTheme);
    fetchClipboard();
    setInterval(() => fetchClipboard(false, true), POLL_MS);
});
