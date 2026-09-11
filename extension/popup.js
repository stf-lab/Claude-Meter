function getColor(pct) {
  if (pct < 80) return "#D97757";
  return "#E84E4E";
}

async function update() {
  const data = await chrome.storage.local.get(["pct5", "pct7", "resetsIn", "status"]);

  const el5 = document.getElementById("pct5");
  const el7 = document.getElementById("pct7");
  const elReset = document.getElementById("reset");
  const elMeter = document.getElementById("meter5h");
  const elStatus = document.getElementById("status");

  if (data.status === "connected" && data.pct5 !== undefined && data.pct5 !== null) {
    el5.textContent = data.pct5 + "%";
    el7.textContent = data.pct7 !== null && data.pct7 !== undefined ? data.pct7 + "%" : "—";
    elReset.textContent = data.resetsIn || "—";
    elMeter.style.width = Math.max(data.pct5, 2) + "%";
    elMeter.style.background = getColor(data.pct5);
    elStatus.textContent = "";
  } else {
    el5.textContent = "—";
    el7.textContent = "—";
    elReset.textContent = "—";
    elMeter.style.width = "0%";
    elStatus.textContent = data.status || "Not connected";
  }
}

document.getElementById("refreshBtn").addEventListener("click", async () => {
  document.getElementById("status").textContent = "Refreshing...";
  // Trigger background poll
  chrome.runtime.sendMessage({ action: "refresh" });
  setTimeout(update, 3000);
});

// Listen for storage changes
chrome.storage.onChanged.addListener(() => update());

update();
