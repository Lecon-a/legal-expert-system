let ragReady = false;

/* ================= FILE SELECT ================= */
document.getElementById("documentInput").addEventListener("change", function () {
    const file = this.files[0];
    if (!file) return;

    document.getElementById("selectedFile").innerText = file.name;

    const reader = new FileReader();
    reader.onload = e => {
        document.getElementById("pdfPreview").src = e.target.result;
    };
    reader.readAsDataURL(file);
});


/* ================= UPLOAD ================= */
document.getElementById("uploadBtn").addEventListener("click", uploadDocument);

async function uploadDocument() {
    const input = document.getElementById("documentInput");
    const status = document.getElementById("uploadStatus");

    if (!input.files.length) {
        alert("Select file first");
        return;
    }

    const formData = new FormData();
    formData.append("document", input.files[0]);

    try {
        status.innerText = "Uploading...";
        status.className = "status status-loading";

        const res = await fetch("/upload", { method: "POST", body: formData });
        const data = await res.json();

        if (!data.success) throw new Error(data.message);

        status.innerText = data.message || "Upload successful";
        status.className = "status status-success";

        // classification UI
        document.getElementById("category").innerText = data.category || "N/A";
        document.getElementById("confidence").innerText = data.confidence || "N/A";
        document.getElementById("reasoning").innerText = data.reasoning || "";

        document.getElementById("classificationResult").style.display = "block";

        startRagProgress();

    } catch (err) {
        status.innerText = "❌ " + err.message;
        status.className = "status status-error";
    }
}


/* ================= PROGRESS ================= */
function startRagProgress() {
    document.getElementById("ragProgress").style.display = "block";

    let progress = 0;
    const bar = document.getElementById("ragProgressBar");

    const interval = setInterval(() => {
        progress += 10;
        bar.style.width = `${progress}%`;

        if (progress >= 100) {
            clearInterval(interval);
            ragReady = true;
        }
    }, 400);
}


/* ================= CHAT ================= */
document.getElementById("askBtn").addEventListener("click", askQuestion);
document.getElementById("questionInput").addEventListener("keydown", e => {
    if (e.key === "Enter") askQuestion();
});

function askQuestion() {
    const input = document.getElementById("questionInput");
    const question = input.value.trim();

    if (!question) return;
    if (!ragReady) return alert("Document still processing. Please wait...");

    const chat = document.getElementById("chatWindow");

    const user = document.createElement("div");
    user.className = "chat-message user-message";
    user.innerHTML = `<div class="bubble">${question}</div>`;
    chat.appendChild(user);

    input.value = "";

    const agent = document.createElement("div");
    agent.className = "chat-message agent-message";
    agent.innerHTML = `
        <div class="avatar">⚖️</div>
        <div class="bubble typing">Analyzing...</div>
    `;
    chat.appendChild(agent);

    scrollChat(true);

    input.disabled = true;
    document.getElementById("askBtn").disabled = true;

    const formData = new FormData();
    formData.append("question", question);

    fetch("/ask", { method: "POST", body: formData })
        .then(res => res.json())
        .then(data => {
            const bubble = agent.querySelector(".bubble");
            bubble.classList.remove("typing");

            if (!data.answer) {
                bubble.innerText = "No response.";
                return;
            }

            streamAnswer(bubble, data.answer);
            saveConversation(question, data.answer);
        })
        .catch(err => {
            agent.querySelector(".bubble").innerText = "Error: " + err.message;
        })
        .finally(() => {
            input.disabled = false;
            document.getElementById("askBtn").disabled = false;
            input.focus();
        });
}


/* ================= STREAMING ================= */
function streamAnswer(element, text, speed = 8) {
    element.innerHTML = "";
    let i = 0;

    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            scrollChat();
            setTimeout(type, speed);
        } else {
            renderAnswer(element, element.innerText);
        }
    }

    type();
}


/* ================= RENDER ================= */
function renderAnswer(element, text) {
    const sections = {
        "SUMMARY": "",
        "KEY PROVISIONS": "",
        "LEGAL ANALYSIS": "",
        "CONCLUSION": ""
    };

    let current = null;

    text.split("\n").forEach(line => {
        line = line.trim();

        const clean = line.replace(":", "");

        if (sections.hasOwnProperty(clean)) {
            current = clean;
        } else if (current) {
            sections[current] += line + " ";
        }
    });

    let html = `<div class="answer">`;
    let hasContent = false;

    for (let key in sections) {
        if (sections[key].trim()) {
            hasContent = true;
            html += `
                <div class="section">
                    <div class="section-title">${key}</div>
                    <div class="section-body">${sections[key]}</div>
                </div>
            `;
        }
    }

    if (!hasContent) html += `<div class="section-body">${text}</div>`;
    html += `</div>`;

    element.innerHTML = html;
}


/* ================= SMART SCROLL ================= */
function scrollChat(force = false) {
    const chat = document.getElementById("chatWindow");
    const nearBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 120;

    if (force || nearBottom) chat.scrollTop = chat.scrollHeight;
}


/* ================= HISTORY ================= */
let history = JSON.parse(localStorage.getItem("legalHistory") || "[]");

function saveConversation(question, answer) {
    history.push({ question, answer, time: Date.now() });

    localStorage.setItem("legalHistory", JSON.stringify(history));
    renderHistory();
}

function renderHistory() {
    const list = document.getElementById("historyList");
    list.innerHTML = "";

    history.slice().reverse().forEach(item => {
        const div = document.createElement("div");
        div.className = "history-item";

        div.innerHTML = `
            <strong>${item.question.slice(0, 40)}...</strong>
            <div style="font-size: .75rem; color:#94a3b8">
                ${new Date(item.time).toLocaleString()}
            </div>
        `;

        div.addEventListener("click", () => restoreConversation(item));
        list.appendChild(div);
    });
}

function restoreConversation(item) {
    const chat = document.getElementById("chatWindow");
    chat.innerHTML = `
        <div class="chat-message user-message">
            <div class="bubble">${item.question}</div>
        </div>
        <div class="chat-message agent-message">
            <div class="bubble">${item.answer}</div>
        </div>
    `;

    scrollChat(true);
}

renderHistory();


/* ================= SIDEBAR TOGGLE ================= */
/* Only ONE clean toggle — fixed shifting issue */
const container = document.querySelector(".container");
const historySidebar = document.getElementById("historySidebar");

document.getElementById("toggleHistory").addEventListener("click", () => {
    historySidebar.classList.toggle("open");
    container.classList.toggle("sidebar-open");  // overlay only
});

document.getElementById("clearHistoryBtn").addEventListener("click", () => {
    if (confirm("Clear history?")) {
        localStorage.removeItem("legalHistory");
        history = [];
        renderHistory();
    }
});