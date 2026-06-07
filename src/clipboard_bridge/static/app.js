(() => {
    "use strict";

    const STORAGE_KEY = "clipboard_bridge_pin";
    const HOTKEY_LABEL = "\u2303A";  // Ctrl+A symbol

    // --- Elements ---------------------------------------------------------
    const tabsEl = document.getElementById("tabs");
    const tabButtons = tabsEl.querySelectorAll(".tab");

    const pinScreen = document.getElementById("pin-screen");
    const notepadScreen = document.getElementById("notepad-screen");
    const autotypeScreen = document.getElementById("autotype-screen");

    const pinForm = document.getElementById("pin-form");
    const pinInput = document.getElementById("pin-input");
    const pinStatus = document.getElementById("pin-status");

    const sendForm = document.getElementById("send-form");
    const textInput = document.getElementById("text-input");
    const sendStatus = document.getElementById("send-status");
    const forgetBtn = document.getElementById("forget-btn");

    const autotypeForm = document.getElementById("autotype-form");
    const autotypeInput = document.getElementById("autotype-input");
    const autotypeSpeed = document.getElementById("autotype-speed");
    const autotypeJitter = document.getElementById("autotype-jitter");
    const autotypeStatus = document.getElementById("autotype-status");
    const autotypeClearBtn = document.getElementById("autotype-clear");
    const forgetBtn2 = document.getElementById("forget-btn-2");

    // --- Helpers ----------------------------------------------------------
    function setStatus(el, message, kind) {
        el.textContent = message;
        el.classList.remove("ok", "err");
        if (kind) el.classList.add(kind);
    }

    function clearStatusLater(el, ms) {
        setTimeout(() => {
            if (el.classList.contains("ok")) setStatus(el, "", null);
        }, ms);
    }

    async function postJSON(url, body) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        let data = {};
        try { data = await res.json(); } catch (_) { /* ignore */ }
        return { status: res.status, data };
    }

    function getPin() {
        return localStorage.getItem(STORAGE_KEY);
    }

    function clearPinAndShowEntry() {
        localStorage.removeItem(STORAGE_KEY);
        showAuthed(false);
        showScreen("pin");
    }

    // --- Screen management -----------------------------------------------
    function showScreen(which) {
        pinScreen.classList.toggle("hidden", which !== "pin");
        notepadScreen.classList.toggle("hidden", which !== "clipboard");
        autotypeScreen.classList.toggle("hidden", which !== "autotype");

        if (which === "pin") {
            setTimeout(() => pinInput.focus(), 50);
        } else if (which === "clipboard") {
            setTimeout(() => textInput.focus(), 50);
        } else if (which === "autotype") {
            setTimeout(() => autotypeInput.focus(), 50);
        }
    }

    function showAuthed(authed) {
        tabsEl.classList.toggle("hidden", !authed);
    }

    function setActiveTab(tab) {
        tabButtons.forEach(b => {
            b.classList.toggle("active", b.dataset.tab === tab);
        });
        showScreen(tab);
    }

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
    });

    // --- PIN flow ---------------------------------------------------------
    async function verifyPin(pin) {
        try {
            return await postJSON("/verify", { pin });
        } catch (_) {
            return { status: 0, data: { error: "Connection failed. Check Wi-Fi." } };
        }
    }

    pinForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const pin = pinInput.value.trim();
        if (!/^\d{4}$/.test(pin)) {
            setStatus(pinStatus, "PIN must be 4 digits.", "err");
            return;
        }
        setStatus(pinStatus, "Checking...", null);
        const { status, data } = await verifyPin(pin);
        if (status === 200 && data.ok) {
            localStorage.setItem(STORAGE_KEY, pin);
            setStatus(pinStatus, "", null);
            pinInput.value = "";
            showAuthed(true);
            setActiveTab("clipboard");
        } else if (status === 0) {
            setStatus(pinStatus, data.error || "Connection failed.", "err");
        } else {
            setStatus(pinStatus, data.error || "PIN rejected.", "err");
        }
    });

    [forgetBtn, forgetBtn2].forEach(b => {
        if (b) b.addEventListener("click", clearPinAndShowEntry);
    });

    // --- Clipboard send ---------------------------------------------------
    sendForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const pin = getPin();
        if (!pin) { clearPinAndShowEntry(); return; }
        const text = textInput.value;
        if (!text) {
            setStatus(sendStatus, "Type something first.", "err");
            return;
        }
        setStatus(sendStatus, "Sending...", null);
        let result;
        try {
            result = await postJSON("/clipboard", { pin, text });
        } catch (_) {
            setStatus(sendStatus, "Connection failed. Check Wi-Fi.", "err");
            return;
        }
        const { status, data } = result;
        if (status === 200 && data.ok) {
            setStatus(sendStatus, "\u2713 Sent to Mac clipboard", "ok");
            clearStatusLater(sendStatus, 2000);
        } else if (status === 401) {
            clearPinAndShowEntry();
        } else if (status === 429) {
            setStatus(sendStatus, data.error || "Locked out. Wait a minute.", "err");
        } else {
            setStatus(sendStatus, data.error || "Send failed.", "err");
        }
    });

    // --- Autotype submit --------------------------------------------------
    autotypeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const pin = getPin();
        if (!pin) { clearPinAndShowEntry(); return; }
        const text = autotypeInput.value;
        if (!text) {
            setStatus(autotypeStatus, "Paste some text first.", "err");
            return;
        }
        setStatus(autotypeStatus, "Queueing...", null);
        let result;
        try {
            result = await postJSON("/autotype", {
                pin,
                text,
                speed: autotypeSpeed.value,
                jitter: autotypeJitter.checked,
            });
        } catch (_) {
            setStatus(autotypeStatus, "Connection failed. Check Wi-Fi.", "err");
            return;
        }
        const { status, data } = result;
        if (status === 200 && data.ok) {
            setStatus(
                autotypeStatus,
                `\u2713 Queued (${data.total} chars). Press ${HOTKEY_LABEL} on Mac to type. Press again to retype.`,
                "ok"
            );
        } else if (status === 401) {
            clearPinAndShowEntry();
        } else if (status === 409) {
            setStatus(autotypeStatus, data.error || "Already typing.", "err");
        } else if (status === 429) {
            setStatus(autotypeStatus, data.error || "Locked out.", "err");
        } else {
            setStatus(autotypeStatus, data.error || "Queue failed.", "err");
        }
    });

    autotypeClearBtn.addEventListener("click", async () => {
        const pin = getPin();
        if (!pin) { clearPinAndShowEntry(); return; }
        try {
            const { status } = await postJSON("/autotype/clear", { pin });
            if (status === 200) {
                setStatus(autotypeStatus, "Queue cleared.", null);
            } else if (status === 401) {
                clearPinAndShowEntry();
            }
        } catch (_) {
            setStatus(autotypeStatus, "Connection failed.", "err");
        }
    });

    // --- Boot -------------------------------------------------------------
    (async function boot() {
        const stored = getPin();
        if (!stored) {
            showAuthed(false);
            showScreen("pin");
            return;
        }
        const { status } = await verifyPin(stored);
        if (status === 200) {
            showAuthed(true);
            setActiveTab("clipboard");
        } else {
            clearPinAndShowEntry();
        }
    })();
})();
