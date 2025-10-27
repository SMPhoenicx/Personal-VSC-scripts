const io = require("socket.io-client");
const socket = io("http://ec2-18-217-125-108.us-east-2.compute.amazonaws.com:5000", {
  path: "/socket.io"
});

socket.on("connect", () => {
  console.log("✅ Connected, session id:", socket.id);
  // join the session you started via /start
  socket.emit("join_session", { session_id: "fecd8b56-0411-4275-95ae-2cc0ef0c1d7d" });
});

socket.on("scraper_update", (data) => {
  console.log("🌀 scraper_update:", data);
});

socket.on("disconnect", (reason) => {
  console.log("❌ Disconnected:", reason);
});
