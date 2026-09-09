(function () {
  var script = document.currentScript;
  var tenant = script.getAttribute("data-tenant") || "kite";
  var origin = new URL(script.src).origin;

  var open = false;
  var frame = null;

  var bubble = document.createElement("button");
  bubble.setAttribute("aria-label", "Open support chat");
  bubble.style.cssText = [
    "position:fixed", "right:20px", "bottom:20px", "width:56px", "height:56px",
    "border-radius:9999px", "border:none", "cursor:pointer", "z-index:2147483000",
    "background:#1a1815", "color:#faf3ec", "font-size:24px", "line-height:56px",
    "text-align:center", "box-shadow:0 8px 24px rgba(0,0,0,0.25)",
    "font-family:-apple-system,Segoe UI,sans-serif",
  ].join(";");
  bubble.textContent = "💬";

  function sizeFrame() {
    var mobile = window.innerWidth < 480;
    frame.style.width = mobile ? "calc(100vw - 24px)" : "380px";
    frame.style.height = mobile ? "70vh" : "600px";
    frame.style.right = mobile ? "12px" : "20px";
    frame.style.bottom = mobile ? "88px" : "88px";
  }

  function toggle() {
    open = !open;
    if (open) {
      if (!frame) {
        frame = document.createElement("iframe");
        frame.src = origin + "/widget?tenant=" + encodeURIComponent(tenant);
        frame.style.cssText = [
          "position:fixed", "border:none", "border-radius:16px",
          "box-shadow:0 20px 60px rgba(0,0,0,0.3)", "z-index:2147483000",
          "background:transparent",
        ].join(";");
        document.body.appendChild(frame);
        sizeFrame();
        window.addEventListener("resize", sizeFrame);
      }
      frame.style.display = "block";
      bubble.textContent = "✕";
    } else {
      if (frame) frame.style.display = "none";
      bubble.textContent = "💬";
    }
  }

  bubble.addEventListener("click", toggle);

  function mount() {
    document.body.appendChild(bubble);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
