// ============================================================
// GLOBAL VARIABLES
// ============================================================

let currentUrl = "";
let currentTitle = "";

let selectedQuality = 720;
let availableQualities = [];

let currentJobId = null;

let downloadTimer = null;
let downloadStartTime = null;

let progressPollingTimer = null;


// ============================================================
// ELEMENTS
// ============================================================

const youtubeUrl =
    document.getElementById("youtubeUrl");

const infoBtn =
    document.getElementById("infoBtn");

const errorMessage =
    document.getElementById("errorMessage");

const loadingCard =
    document.getElementById("loadingCard");

const loadingTitle =
    document.getElementById("loadingTitle");

const loadingText =
    document.getElementById("loadingText");

const videoCard =
    document.getElementById("videoCard");

const qualitySection =
    document.getElementById("qualitySection");

const downloadSection =
    document.getElementById("downloadSection");

const thumbnail =
    document.getElementById("thumbnail");

const videoTitle =
    document.getElementById("videoTitle");

const uploader =
    document.getElementById("uploader");

const duration =
    document.getElementById("duration");

const folderName =
    document.getElementById("folderName");

const qualityGrid =
    document.getElementById("qualityGrid");

const selectedQualityElement =
    document.getElementById("selectedQuality");

const downloadVideoBtn =
    document.getElementById("downloadVideoBtn");

const downloadAudioBtn =
    document.getElementById("downloadAudioBtn");

const downloadThumbnailBtn =
    document.getElementById("downloadThumbnailBtn");

const downloadDetailsBtn =
    document.getElementById("downloadDetailsBtn");

const downloadAllBtn =
    document.getElementById("downloadAllBtn");

const progressCard =
    document.getElementById("progressCard");

const progressText =
    document.getElementById("progressText");

const progressPercent =
    document.getElementById("progressPercent");

const progressFill =
    document.getElementById("progressFill");

const resultCard =
    document.getElementById("resultCard");

const resultText =
    document.getElementById("resultText");

const downloadTimerElement =
    document.getElementById("downloadTimer");

const downloadSpeed =
    document.getElementById("downloadSpeed");

const downloadEta =
    document.getElementById("downloadEta");


// ============================================================
// ERROR
// ============================================================

function showError(message) {

    errorMessage.textContent = message;

    errorMessage.style.display = "block";
}


function hideError() {

    errorMessage.textContent = "";

    errorMessage.style.display = "none";
}


// ============================================================
// LOADING
// ============================================================

function showLoading(title, text) {

    loadingTitle.textContent = title;

    loadingText.textContent = text;

    loadingCard.classList.remove("hidden");
}


function hideLoading() {

    loadingCard.classList.add("hidden");
}


// ============================================================
// DURATION
// ============================================================

function formatDuration(seconds) {

    if (!seconds) {
        return "00:00";
    }

    seconds = Number(seconds);

    const hours =
        Math.floor(seconds / 3600);

    const minutes =
        Math.floor(
            (seconds % 3600) / 60
        );

    const secs =
        Math.floor(seconds % 60);

    if (hours > 0) {

        return (
            String(hours).padStart(2, "0") +
            ":" +
            String(minutes).padStart(2, "0") +
            ":" +
            String(secs).padStart(2, "0")
        );
    }

    return (
        String(minutes).padStart(2, "0") +
        ":" +
        String(secs).padStart(2, "0")
    );
}


// ============================================================
// DOWNLOAD TIMER
// ============================================================

function formatElapsedTime(seconds) {

    seconds = Math.max(
        0,
        Math.floor(seconds)
    );

    const hours =
        Math.floor(seconds / 3600);

    const minutes =
        Math.floor(
            (seconds % 3600) / 60
        );

    const secs =
        seconds % 60;

    if (hours > 0) {

        return (
            String(hours).padStart(2, "0") +
            ":" +
            String(minutes).padStart(2, "0") +
            ":" +
            String(secs).padStart(2, "0")
        );
    }

    return (
        String(minutes).padStart(2, "0") +
        ":" +
        String(secs).padStart(2, "0")
    );
}


function startDownloadTimer() {

    stopDownloadTimer();

    downloadStartTime = Date.now();

    if (downloadTimerElement) {

        downloadTimerElement.textContent =
            "00:00";
    }

    downloadTimer =
        setInterval(() => {

            if (!downloadStartTime) {
                return;
            }

            const elapsed =
                (
                    Date.now() -
                    downloadStartTime
                ) / 1000;

            if (downloadTimerElement) {

                downloadTimerElement.textContent =
                    formatElapsedTime(elapsed);
            }

        }, 1000);
}


function stopDownloadTimer(finalSeconds = null) {

    if (downloadTimer) {

        clearInterval(
            downloadTimer
        );

        downloadTimer = null;
    }

    if (
        finalSeconds !== null &&
        downloadTimerElement
    ) {

        downloadTimerElement.textContent =
            formatElapsedTime(finalSeconds);

    } else if (
        downloadStartTime &&
        downloadTimerElement
    ) {

        const elapsed =
            (
                Date.now() -
                downloadStartTime
            ) / 1000;

        downloadTimerElement.textContent =
            formatElapsedTime(elapsed);
    }
}


// ============================================================
// PROGRESS
// ============================================================

function setProgress(
    percent,
    text
) {

    const value =
        Math.max(
            0,
            Math.min(
                100,
                Number(percent) || 0
            )
        );

    progressFill.style.width =
        `${value}%`;

    progressPercent.textContent =
        `${Math.round(value)}%`;

    progressText.textContent =
        text || "Downloading...";
}


function showProgress(text) {

    progressCard.classList.remove(
        "hidden"
    );

    setProgress(
        0,
        text
    );
}


function hideProgress() {

    progressCard.classList.add(
        "hidden"
    );
}


// ============================================================
// RESULT
// ============================================================

function showResult(message) {

    resultText.textContent =
        message;

    resultCard.classList.remove(
        "hidden"
    );

    setTimeout(() => {

        resultCard.classList.add(
            "hidden"
        );

    }, 7000);
}


// ============================================================
// QUALITY
// ============================================================

function renderQualities() {

    qualityGrid.innerHTML = "";

    const standardQualities = [
        360,
        480,
        720,
        1080,
        1440,
        2160
    ];

    standardQualities.forEach(
        (quality) => {

            const button =
                document.createElement(
                    "button"
                );

            button.className =
                "quality-btn";

            button.textContent =
                quality === 1440
                    ? "2K"
                    : quality === 2160
                        ? "4K"
                        : `${quality}p`;

            const isAvailable =
                availableQualities.includes(
                    quality
                );

            if (!isAvailable) {

                button.classList.add(
                    "disabled"
                );

                button.disabled = true;

            } else {

                button.addEventListener(
                    "click",
                    () =>
                        selectQuality(
                            quality
                        )
                );
            }

            if (
                quality === selectedQuality &&
                isAvailable
            ) {

                button.classList.add(
                    "active"
                );
            }

            qualityGrid.appendChild(
                button
            );
        }
    );

    updateSelectedQuality();
}


function selectQuality(quality) {

    selectedQuality =
        quality;

    updateSelectedQuality();

    renderQualities();
}


function updateSelectedQuality() {

    let label =
        `${selectedQuality}p`;

    if (selectedQuality === 1440) {
        label = "2K";
    }

    if (selectedQuality === 2160) {
        label = "4K";
    }

    selectedQualityElement.textContent =
        label;
}


// ============================================================
// CREATE SERVER JOB
// ============================================================

async function createDownloadJob() {

    try {

        const response =
            await fetch(
                "/create-job",
                {
                    method: "POST"
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.error ||
                "Could not create download job."
            );
        }

        currentJobId =
            data.job_id;

        return currentJobId;

    } catch (error) {

        console.error(
            "Job creation error:",
            error
        );

        throw error;
    }
}


// ============================================================
// POLL SERVER PROGRESS
// ============================================================

function startProgressPolling() {

    stopProgressPolling();

    if (!currentJobId) {
        return;
    }

    progressPollingTimer =
        setInterval(
            async () => {

                try {

                    const response =
                        await fetch(
                            `/progress/${currentJobId}`
                        );

                    if (!response.ok) {
                        return;
                    }

                    const data =
                        await response.json();

                    updateProgressFromServer(
                        data
                    );

                } catch (error) {

                    console.warn(
                        "Progress polling error:",
                        error
                    );
                }

            },
            500
        );
}


function stopProgressPolling() {

    if (progressPollingTimer) {

        clearInterval(
            progressPollingTimer
        );

        progressPollingTimer = null;
    }
}


function updateProgressFromServer(
    data
) {

    if (!data) {
        return;
    }

    if (
        typeof data.progress ===
        "number"
    ) {

        setProgress(
            data.progress,
            data.message ||
            "Downloading..."
        );
    }


    if (downloadSpeed) {

        downloadSpeed.textContent =
            data.speed || "--";
    }


    if (downloadEta) {

        downloadEta.textContent =
            data.eta || "--";
    }


    if (
        data.elapsed !== undefined &&
        data.elapsed !== null &&
        downloadTimerElement &&
        data.status === "completed"
    ) {

        stopDownloadTimer(
            Number(data.elapsed)
        );
    }


    if (data.message) {

        progressText.textContent =
            data.message;
    }
}


// ============================================================
// GET VIDEO INFORMATION
// ============================================================

infoBtn.addEventListener(
    "click",
    getVideoInfo
);


youtubeUrl.addEventListener(
    "keydown",
    (event) => {

        if (event.key === "Enter") {

            getVideoInfo();
        }

    }
);


async function getVideoInfo() {

    hideError();

    resultCard.classList.add(
        "hidden"
    );

    const url =
        youtubeUrl.value.trim();

    if (!url) {

        showError(
            "Please paste a YouTube video URL."
        );

        youtubeUrl.focus();

        return;
    }


    currentUrl =
        url;

    videoCard.classList.add(
        "hidden"
    );

    qualitySection.classList.add(
        "hidden"
    );

    downloadSection.classList.add(
        "hidden"
    );


    showLoading(
        "Getting video information",
        "Please wait while we read the video information..."
    );


    infoBtn.disabled = true;

    infoBtn.textContent =
        "Loading...";


    try {

        const response =
            await fetch(
                "/info",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            url: url
                        })
                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.error ||
                "Unable to get video information."
            );
        }


        currentTitle =
            data.title ||
            "YouTube Video";


        availableQualities =
            data.qualities || [];


        thumbnail.src =
            data.thumbnail || "";


        videoTitle.textContent =
            data.title ||
            "YouTube Video";


        uploader.textContent =
            data.uploader ||
            "YouTube";


        duration.textContent =
            formatDuration(
                data.duration
            );


        folderName.textContent =
            `downloads/${data.title}/`;


        if (
            availableQualities.length > 0
        ) {

            const preferred =
                [
                    2160,
                    1440,
                    1080,
                    720,
                    480,
                    360
                ].find(
                    q =>
                        availableQualities.includes(
                            q
                        )
                );

            selectedQuality =
                preferred ||
                availableQualities[0];

        } else {

            selectedQuality =
                720;
        }


        renderQualities();


        videoCard.classList.remove(
            "hidden"
        );

        qualitySection.classList.remove(
            "hidden"
        );

        downloadSection.classList.remove(
            "hidden"
        );


        hideLoading();

    } catch (error) {

        hideLoading();

        showError(
            error.message ||
            "Something went wrong."
        );

    } finally {

        infoBtn.disabled = false;

        infoBtn.innerHTML =
            "<span>🔍</span> Get Video";
    }
}


// ============================================================
// DOWNLOAD FILE
// ============================================================

async function downloadFile(
    endpoint,
    body,
    type
) {

    hideError();

    showProgress(
        `Preparing ${type} download...`
    );


    // Reset stats

    if (downloadSpeed) {
        downloadSpeed.textContent = "--";
    }

    if (downloadEta) {
        downloadEta.textContent = "--";
    }


    // START TIMER

    startDownloadTimer();


    try {

        // Create server-side job

        currentJobId =
            await createDownloadJob();


        // Start live progress polling

        startProgressPolling();


        // Add job ID to request

        const requestBody = {
            ...body,
            job_id: currentJobId
        };


        const response =
            await fetch(
                endpoint,
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            requestBody
                        )
                }
            );


        if (!response.ok) {

            let errorMessage =
                "Download failed.";

            try {

                const errorData =
                    await response.json();

                errorMessage =
                    errorData.error ||
                    errorMessage;

            } catch (e) {

                // Not JSON
            }

            throw new Error(
                errorMessage
            );
        }


        // Server progress = 100

        setProgress(
            100,
            `${type} download completed`
        );


        // Get filename

        const contentDisposition =
            response.headers.get(
                "Content-Disposition"
            );


        let filename =
            `${currentTitle}-${type}`;


        if (contentDisposition) {

            const utf8Match =
                contentDisposition.match(
                    /filename\*=UTF-8''([^;]+)/i
                );

            const normalMatch =
                contentDisposition.match(
                    /filename="?([^"]+)"?/i
                );

            if (
                utf8Match &&
                utf8Match[1]
            ) {

                try {

                    filename =
                        decodeURIComponent(
                            utf8Match[1]
                        );

                } catch (e) {

                    filename =
                        utf8Match[1];
                }

            } else if (
                normalMatch &&
                normalMatch[1]
            ) {

                filename =
                    normalMatch[1];
            }
        }


        // Convert response to Blob

        const blob =
            await response.blob();


        const blobUrl =
            window.URL.createObjectURL(
                blob
            );


        const link =
            document.createElement(
                "a"
            );


        link.href =
            blobUrl;

        link.download =
            filename;


        document.body.appendChild(
            link
        );

        link.click();

        link.remove();


        window.URL.revokeObjectURL(
            blobUrl
        );


        // Get final server time

        let finalElapsed =
            null;


        try {

            const finalResponse =
                await fetch(
                    `/progress/${currentJobId}`
                );

            if (finalResponse.ok) {

                const finalData =
                    await finalResponse.json();

                if (
                    finalData.elapsed !==
                    undefined
                ) {

                    finalElapsed =
                        Number(
                            finalData.elapsed
                        );
                }
            }

        } catch (e) {

            // Ignore
        }


        // STOP TIMER

        stopDownloadTimer(
            finalElapsed
        );


        showResult(
            `${type} downloaded successfully.`
        );


    } catch (error) {

        stopDownloadTimer();

        showError(
            error.message ||
            `${type} download failed.`
        );

        hideProgress();

    } finally {

        stopProgressPolling();

        currentJobId = null;
    }
}


// ============================================================
// VIDEO DOWNLOAD
// ============================================================

downloadVideoBtn.addEventListener(
    "click",
    async () => {

        if (!currentUrl) {

            showError(
                "Please get video information first."
            );

            return;
        }


        downloadVideoBtn.disabled =
            true;

        downloadVideoBtn.textContent =
            "Downloading...";


        await downloadFile(
            "/download/video",
            {
                url: currentUrl,
                quality: selectedQuality
            },
            "Video"
        );


        downloadVideoBtn.disabled =
            false;

        downloadVideoBtn.textContent =
            "Download";
    }
);


// ============================================================
// AUDIO DOWNLOAD
// ============================================================

downloadAudioBtn.addEventListener(
    "click",
    async () => {

        if (!currentUrl) {

            showError(
                "Please get video information first."
            );

            return;
        }


        downloadAudioBtn.disabled =
            true;

        downloadAudioBtn.textContent =
            "Downloading...";


        await downloadFile(
            "/download/audio",
            {
                url: currentUrl
            },
            "Audio"
        );


        downloadAudioBtn.disabled =
            false;

        downloadAudioBtn.textContent =
            "Download";
    }
);


// ============================================================
// THUMBNAIL DOWNLOAD
// ============================================================

downloadThumbnailBtn.addEventListener(
    "click",
    async () => {

        if (!currentUrl) {

            showError(
                "Please get video information first."
            );

            return;
        }


        downloadThumbnailBtn.disabled =
            true;

        downloadThumbnailBtn.textContent =
            "Downloading...";


        await downloadFile(
            "/download/thumbnail",
            {
                url: currentUrl
            },
            "Thumbnail"
        );


        downloadThumbnailBtn.disabled =
            false;

        downloadThumbnailBtn.textContent =
            "Download";
    }
);


// ============================================================
// DETAILS DOWNLOAD
// ============================================================

downloadDetailsBtn.addEventListener(
    "click",
    async () => {

        if (!currentUrl) {

            showError(
                "Please get video information first."
            );

            return;
        }


        downloadDetailsBtn.disabled =
            true;

        downloadDetailsBtn.textContent =
            "Creating...";


        await downloadFile(
            "/download/details",
            {
                url: currentUrl,
                quality: selectedQuality
            },
            "Details"
        );


        downloadDetailsBtn.disabled =
            false;

        downloadDetailsBtn.textContent =
            "Download";
    }
);


// ============================================================
// DOWNLOAD ALL
// ============================================================

downloadAllBtn.addEventListener(
    "click",
    async () => {

        if (!currentUrl) {

            showError(
                "Please get video information first."
            );

            return;
        }


        downloadAllBtn.disabled =
            true;

        downloadAllBtn.textContent =
            "Preparing All Files...";


        await downloadFile(
            "/download/all",
            {
                url: currentUrl,
                quality: selectedQuality
            },
            "All Files"
        );


        downloadAllBtn.disabled =
            false;

        downloadAllBtn.textContent =
            "📦 Download All Files";
    }
);