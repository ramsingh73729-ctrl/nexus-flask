(() => {
  const rewardButton = document.getElementById("claimReward");
  const rewardStatus = document.getElementById("rewardStatus");
  const activityList = document.getElementById("activityList");
  const leaderboard = document.getElementById("dashboardLeaderboard");
  const toast = document.getElementById("nexusToast");
  let rewardPending = false;

  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || "";
  }

  function showToast(message, type = "info") {
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast access-toast toast-${type}`;
    toast.hidden = false;
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "JUST NOW";
    return date.toLocaleString([], {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    }).toUpperCase() + " UTC";
  }

  function updateUser(user) {
    if (!user) return;
    const level = Number(user.level) || 1;
    const totalXp = Number(user.total_xp) || 0;
    const levelXp = totalXp - ((level - 1) * 100);
    const percent = Math.max(0, Math.min(100, levelXp));
    const values = {
      dashboardLevel: `LVL ${level}`,
      dashboardLevelLine: `LEVEL ${level}`,
      dashboardRank: user.rank || "Recruit",
      dashboardXp: `${totalXp} TOTAL XP`,
      dashboardTotalXp: String(totalXp),
      dashboardStreak: String(Number(user.current_login_streak) || 0),
    };
    Object.entries(values).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value;
    });
    const progress = document.getElementById("dashboardXpTrack");
    if (progress) progress.style.width = `${percent}%`;
  }

  function renderEmpty(container, title, message) {
    container.replaceChildren();
    const empty = document.createElement("div");
    empty.className = "empty-state compact-empty";
    const mark = document.createElement("span");
    mark.textContent = "⌁";
    const heading = document.createElement("strong");
    heading.textContent = title;
    const copy = document.createElement("p");
    copy.textContent = message;
    empty.append(mark, heading, copy);
    container.append(empty);
  }

  function renderActivities(items) {
    if (!activityList) return;
    if (!items?.length) {
      renderEmpty(activityList, "No signals yet.", "Play your first Neon Runner session and your activity will appear here.");
      return;
    }
    activityList.replaceChildren();
    items.forEach((item) => {
      const article = document.createElement("article");
      article.className = "activity-item";
      const mark = document.createElement("span");
      mark.className = "activity-mark";
      mark.textContent = "✦";
      const content = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = item.description || "NEXUS activity";
      const meta = document.createElement("small");
      const xp = Number(item.xp_earned) > 0 ? ` · +${Number(item.xp_earned)} XP` : "";
      meta.textContent = `${formatDate(item.created_at)}${xp}`;
      content.append(title, meta);
      article.append(mark, content);
      activityList.append(article);
    });
  }

  function renderLeaderboard(entries) {
    if (!leaderboard) return;
    if (!entries?.length) {
      renderEmpty(leaderboard, "Board is open.", "Be the first player to lock in a score.");
      return;
    }
    leaderboard.replaceChildren();
    entries.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "leaderboard-row";
      const rank = document.createElement("span");
      rank.textContent = `#${entry.rank}`;
      const name = document.createElement("strong");
      name.textContent = entry.name || "Anonymous player";
      const score = document.createElement("b");
      score.textContent = String(Number(entry.score) || 0);
      row.append(rank, name, score);
      leaderboard.append(row);
    });
  }

  async function loadDashboard() {
    try {
      const response = await fetch("/api/dashboard", {
        headers: { Accept: "application/json" },
      });
      if (response.status === 401) {
        window.location.assign("/");
        return;
      }
      if (!response.ok) return;
      const result = await response.json();
      updateUser(result.user);
      renderActivities(result.activities);
      renderLeaderboard(result.leaderboard);
      if (rewardButton && result.reward_available === false) {
        rewardButton.disabled = true;
        rewardButton.textContent = "Claimed for today";
      }
    } catch (_error) {
      showToast("Live dashboard refresh unavailable.", "error");
    }
  }

  rewardButton?.addEventListener("click", async () => {
    if (rewardPending || rewardButton.disabled) return;
    rewardPending = true;
    rewardButton.disabled = true;
    rewardButton.textContent = "Claiming…";
    if (rewardStatus) rewardStatus.textContent = "SECURING DAILY SIGNAL...";

    try {
      const response = await fetch("/api/daily-reward", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify({}),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(result.message || "Daily reward could not be claimed.");
      }
      updateUser(result.user);
      rewardButton.textContent = "Claimed for today";
      if (rewardStatus) rewardStatus.textContent = result.message || "Reward secured.";
      showToast(result.message || "Daily reward secured.", "success");
      await loadDashboard();
    } catch (error) {
      rewardButton.disabled = false;
      rewardButton.textContent = "Claim +25 XP";
      if (rewardStatus) rewardStatus.textContent = error.message;
      showToast(error.message, "error");
    } finally {
      rewardPending = false;
    }
  });

  loadDashboard();
})();
