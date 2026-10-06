const { spawn } = require("child_process");

const port = process.env.PORT || "5001";
const python = process.env.PYTHON || "python";
const args = ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", port];

console.log("Starting ADI HT9046 FastAPI server...");
console.log(`${python} ${args.join(" ")}`);

const child = spawn(python, args, {
  stdio: "inherit",
  shell: process.platform === "win32",
});

child.on("exit", (code) => process.exit(code || 0));
