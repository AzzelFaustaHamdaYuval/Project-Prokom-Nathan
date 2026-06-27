/* ==================================
   STUDYFOCUS AI
================================== */

document.addEventListener("DOMContentLoaded", () => {

    console.log("StudyFocus AI Loaded");

    startClock();
    animateCards();
    loadStats();

    setInterval(loadStats, 1000);

});

/* ==================================
   REALTIME CLOCK
================================== */

let startTime = Date.now();

function startClock() {

    setInterval(() => {

        const now = Date.now();

        const elapsed =
            Math.floor((now - startTime) / 1000);

        const h =
            String(Math.floor(elapsed / 3600))
            .padStart(2, "0");

        const m =
            String(Math.floor((elapsed % 3600) / 60))
            .padStart(2, "0");

        const s =
            String(elapsed % 60)
            .padStart(2, "0");

        const timer =
            document.getElementById("study_time");

        if(timer){

            timer.textContent =
                `${h}:${m}:${s}`;

        }

    },1000);

}

/* ==================================
   LOAD DATA FLASK
================================== */

async function loadStats() {

    try {

        const response =
            await fetch("/api/stats");

        const data =
            await response.json();

        updateDashboard(data);

    }

    catch(error){

        console.log(
            "API belum aktif, mode demo."
        );

        demoMode();

    }

}

/* ==================================
   UPDATE DASHBOARD
================================== */

function updateDashboard(data){

    updateText(
        "focus_score",
        data.focus_score + "%"
    );

    updateText(
        "eye_state",
        data.eye_state
    );

    updateText(
        "head_state",
        data.head_state
    );

    updateText(
        "posture_state",
        data.posture_state
    );

    updateProgressBar(
        data.focus_score
    );

    updateCategory(
        data.focus_score
    );

}

/* ==================================
   DEMO MODE
================================== */

function demoMode(){

    const score =
        Math.floor(
            Math.random() * 30 + 70
        );

    updateText(
        "focus_score",
        score + "%"
    );

    updateText(
        "eye_state",
        score > 75
            ? "Fokus"
            : "Kurang Fokus"
    );

    updateText(
        "head_state",
        score > 75
            ? "Menghadap Layar"
            : "Menoleh"
    );

    updateText(
        "posture_state",
        score > 75
            ? "Baik"
            : "Kurang Baik"
    );

    updateProgressBar(score);

    updateCategory(score);

}

/* ==================================
   UPDATE TEXT
================================== */

function updateText(id,value){

    const element =
        document.getElementById(id);

    if(element){

        element.textContent = value;

    }

}

/* ==================================
   PROGRESS BAR
================================== */

function updateProgressBar(score){

    const bar =
        document.getElementById("focus_bar");

    const text =
        document.getElementById("focus_text");

    if(!bar) return;

    bar.style.width =
        score + "%";

    if(text){

        text.textContent =
            score + "%";

    }

}

/* ==================================
   FOCUS CATEGORY
================================== */

function updateCategory(score){

    const category =
        document.getElementById(
            "focus_category"
        );

    if(!category) return;

    if(score >= 80){

        category.innerHTML =
            "🟢 Sangat Fokus";

    }

    else if(score >= 60){

        category.innerHTML =
            "🟡 Cukup Fokus";

    }

    else{

        category.innerHTML =
            "🔴 Kurang Fokus";

        showWarning();

    }

}

/* ==================================
   WARNING NOTIFICATION
================================== */

function showWarning(){

    if(
        document.querySelector(
            ".focus-warning"
        )
    ) return;

    const warning =
        document.createElement("div");

    warning.classList.add(
        "focus-warning"
    );

    warning.innerHTML =
        "⚠ Fokus Menurun! Coba Istirahat Sejenak";

    document.body.appendChild(
        warning
    );

    setTimeout(() => {

        warning.remove();

    },5000);

}

/* ==================================
   CARD ANIMATION
================================== */

function animateCards(){

    const cards =
        document.querySelectorAll(
            ".card"
        );

    cards.forEach((card,index)=>{

        card.style.opacity = "0";

        card.style.transform =
            "translateY(20px)";

        setTimeout(()=>{

            card.style.transition =
                "0.6s";

            card.style.opacity = "1";

            card.style.transform =
                "translateY(0px)";

        }, index * 150);

    });

}

/* ==================================
   BUTTON START
================================== */

const startButton =
document.querySelector(
    ".start-btn"
);

if(startButton){

    startButton.addEventListener(
        "click",
        ()=>{

            showToast(
                "▶ Session Dimulai"
            );

        }
    );

}

/* ==================================
   BUTTON STOP
================================== */

const stopButton =
document.querySelector(
    ".stop-btn"
);

if(stopButton){

    stopButton.addEventListener(
        "click",
        ()=>{

            showToast(
                "⏹ Session Dihentikan"
            );

        }
    );

}

/* ==================================
   TOAST
================================== */

function showToast(message){

    const toast =
        document.createElement("div");

    toast.className =
        "toast-message";

    toast.textContent =
        message;

    document.body.appendChild(
        toast
    );

    setTimeout(()=>{

        toast.classList.add(
            "show"
        );

    },100);

    setTimeout(()=>{

        toast.remove();

    },3000);

}

/* ==================================
   TABLE SEARCH
================================== */

const searchInput =
document.getElementById(
    "searchInput"
);

if(searchInput){

    searchInput.addEventListener(
        "keyup",
        ()=>{

            const value =
                searchInput.value
                .toLowerCase();

            const rows =
                document.querySelectorAll(
                    "#historyTable tr"
                );

            rows.forEach(row=>{

                row.style.display =
                    row.textContent
                    .toLowerCase()
                    .includes(value)
                    ? ""
                    : "none";

            });

        }
    );

}

async function startSession() {

    const response = await fetch(
        "/api/session/start",
        {
            method: "POST"
        }
    );

    const data = await response.json();

    console.log(data);

    document.getElementById("video-feed").src =
        "/video_feed?" + Date.now();
}

async function stopSession() {

    const response = await fetch(
        "/api/session/stop",
        {
            method: "POST"
        }
    );

    const data = await response.json();

    console.log(data);

    document.getElementById("video-feed").src = "";
}