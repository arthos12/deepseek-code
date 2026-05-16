import * as vscode from "vscode";
import * as cp from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

let outputChannel: vscode.OutputChannel;
let statusBar: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
  outputChannel = vscode.window.createOutputChannel("DeepSeek Code");
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.text = "$(hubot) DeepSeek";
  statusBar.tooltip = "DeepSeek Code";
  statusBar.command = "deepseek-code.openChat";
  statusBar.show();
  context.subscriptions.push(statusBar);

  context.subscriptions.push(
    vscode.commands.registerCommand("deepseek-code.openChat", () => {
      ChatPanel.createOrShow(context.extensionUri);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("deepseek-code.explainCode", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.document.getText(editor.selection);
      if (!selection) { vscode.window.showWarningMessage("Select some code first."); return; }
      const panel = ChatPanel.createOrShow(context.extensionUri);
      panel.sendPrompt(`Explain this code:\n\`\`\`\n${selection}\n\`\`\``);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("deepseek-code.fixCode", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.document.getText(editor.selection);
      if (!selection) { vscode.window.showWarningMessage("Select some code first."); return; }
      const panel = ChatPanel.createOrShow(context.extensionUri);
      panel.sendPrompt(`Fix bugs, edge cases, and security issues:\n\`\`\`\n${selection}\n\`\`\``);
    })
  );

  outputChannel.appendLine("DeepSeek Code extension activated.");
}

export function deactivate() {
  if (statusBar) statusBar.dispose();
  if (outputChannel) outputChannel.dispose();
}

class ChatPanel {
  public static currentPanel: ChatPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private _disposables: vscode.Disposable[] = [];
  private _cliPath: string;
  private _apiKey: string;

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this._panel = panel;
    this._cliPath = this._findCli();
    this._apiKey = this._findApiKey();
    this._panel.webview.html = this._getHtml();
    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    this._panel.webview.onDidReceiveMessage(this._handleMessage.bind(this), null, this._disposables);
    if (!this._apiKey) {
      this._panel.webview.postMessage({ type: "needKey" });
    }
  }

  public static createOrShow(extensionUri: vscode.Uri): ChatPanel {
    if (ChatPanel.currentPanel) {
      ChatPanel.currentPanel._panel.reveal(vscode.ViewColumn.Beside);
      return ChatPanel.currentPanel;
    }
    const panel = vscode.window.createWebviewPanel("deepseek-code", "DeepSeek Code", vscode.ViewColumn.Beside, {
      enableScripts: true, retainContextWhenHidden: true,
    });
    ChatPanel.currentPanel = new ChatPanel(panel, extensionUri);
    return ChatPanel.currentPanel;
  }

  public sendPrompt(prompt: string) {
    this._panel.webview.postMessage({ type: "userPrompt", prompt });
  }

  private _findApiKey(): string {
    const localSettings = path.join(this._findProjectRoot(), "settings.local.json");
    try {
      if (fs.existsSync(localSettings)) {
        const data = JSON.parse(fs.readFileSync(localSettings, "utf-8"));
        if (data.api_key) return data.api_key;
      }
    } catch {}
    return process.env.DEEPSEEK_API_KEY || "";
  }

  private _findProjectRoot(): string {
    for (const folder of (vscode.workspace.workspaceFolders || [])) {
      const p = path.join(folder.uri.fsPath, "DEEPSEEK.md");
      try { if (fs.existsSync(p)) return folder.uri.fsPath; } catch {}
    }
    return os.homedir();
  }

  private _findCli(): string {
    const candidates = [
      path.join(os.homedir(), ".local", "bin", "deepseek"),
      path.join(os.homedir(), ".venv", "Scripts", "deepseek.exe"),
      "deepseek",
    ];
    for (const c of candidates) {
      try { cp.execSync(`"${c}" --help`, { timeout: 3000, stdio: "ignore" }); return c; }
      catch { continue; }
    }
    return "deepseek";
  }

  private async _handleMessage(message: any) {
    switch (message.type) {
      case "prompt": await this._runCli(message.prompt); break;
      case "setKey":
        this._apiKey = message.key;
        try {
          const root = this._findProjectRoot();
          const p = path.join(root, "settings.local.json");
          const existing = fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf-8")) : {};
          existing.api_key = message.key;
          fs.writeFileSync(p, JSON.stringify(existing, null, 2), "utf-8");
          this._panel.webview.postMessage({ type: "keySaved" });
        } catch (e: any) {
          this._panel.webview.postMessage({ type: "error", text: `Failed to save key: ${e.message}` });
        }
        break;
    }
  }

  private async _runCli(prompt: string) {
    this._panel.webview.postMessage({ type: "thinking" });
    try {
      const env = { ...process.env };
      if (this._apiKey) env.DEEPSEEK_API_KEY = this._apiKey;
      const child = cp.spawn(this._cliPath, ["chat", "-p", prompt], { env, stdio: ["pipe", "pipe", "pipe"] });
      child.stdout.on("data", (data: Buffer) => this._panel.webview.postMessage({ type: "response", text: data.toString("utf-8") }));
      child.stderr.on("data", (data: Buffer) => this._panel.webview.postMessage({ type: "error", text: data.toString("utf-8") }));
      child.on("close", (code: number) => this._panel.webview.postMessage({ type: "done", code }));
      child.stdin.write(prompt + "\n");
      child.stdin.end();
    } catch (e: any) {
      this._panel.webview.postMessage({ type: "error", text: `Failed to run deepseek CLI: ${e.message}` });
    }
  }

  private _getHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DeepSeek Code</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:var(--vscode-font-family); font-size:var(--vscode-font-size); color:var(--vscode-foreground); background:var(--vscode-sideBar-background); padding:12px; height:100vh; display:flex; flex-direction:column; }
#output { flex:1; overflow-y:auto; white-space:pre-wrap; word-break:break-word; margin-bottom:8px; }
#input-row { display:flex; gap:8px; }
#input { flex:1; background:var(--vscode-input-background); color:var(--vscode-input-foreground); border:1px solid var(--vscode-input-border); padding:8px; font-family:inherit; font-size:inherit; resize:none; }
#input:focus { outline:1px solid var(--vscode-focusBorder); }
#send { background:var(--vscode-button-background); color:var(--vscode-button-foreground); border:none; padding:8px 16px; cursor:pointer; font-size:inherit; }
#send:hover { background:var(--vscode-button-hoverBackground); }
#key-area { display:block; padding:8px; margin-bottom:8px; border:1px solid var(--vscode-input-border); }
#key-area input { flex:1; background:var(--vscode-input-background); color:var(--vscode-input-foreground); border:1px solid var(--vscode-input-border); padding:4px 8px; font-family:inherit; }
#key-area button { background:var(--vscode-button-background); color:var(--vscode-button-foreground); border:none; padding:4px 12px; cursor:pointer; }
.thinking { color:var(--vscode-descriptionForeground); font-style:italic; }
.error { color:var(--vscode-errorForeground); }
.done { color:var(--vscode-descriptionForeground); font-size:0.85em; margin-top:4px; }
.user { color:var(--vscode-textLink-foreground); margin-bottom:8px; }
.assistant { margin-bottom:12px; }
</style>
</head>
<body>
<div id="key-area">
  <div style="margin-bottom:4px;">Enter your DeepSeek API key to start.</div>
  <div style="display:flex; gap:8px;">
    <input type="password" id="api-key" placeholder="sk-...">
    <button id="save-key">Save</button>
  </div>
  <div id="key-status" style="margin-top:4px; font-size:0.85em;"></div>
</div>
<div id="output"></div>
<div id="input-row">
  <textarea id="input" rows="2" placeholder="Ask DeepSeek Code... (Enter to send, Shift+Enter for newline)"></textarea>
  <button id="send">Send</button>
</div>
<script>
const vscode = acquireVsCodeApi();
const output = document.getElementById('output');
const input = document.getElementById('input');
function append(text, cls) {
  const div = document.createElement('div');
  div.className = cls || '';
  div.textContent = text;
  output.appendChild(div);
  output.scrollTop = output.scrollHeight;
}
function sendPrompt() {
  const text = input.value.trim();
  if (!text) return;
  append('> ' + text, 'user');
  vscode.postMessage({ type: 'prompt', prompt: text });
  input.value = '';
}
document.getElementById('send').addEventListener('click', sendPrompt);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendPrompt(); }
});
document.getElementById('save-key').addEventListener('click', () => {
  const key = document.getElementById('api-key').value.trim();
  if (key) { vscode.postMessage({ type: 'setKey', key }); }
});
document.getElementById('api-key').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    const key = e.target.value.trim();
    if (key) { vscode.postMessage({ type: 'setKey', key }); }
  }
});
window.addEventListener('message', (e) => {
  switch (e.data.type) {
    case 'response': append(e.data.text, 'assistant'); break;
    case 'thinking': append('...', 'thinking'); break;
    case 'error': append(e.data.text, 'error'); break;
    case 'done': append('', 'done'); break;
    case 'needKey': document.getElementById('key-area').style.display = 'block'; break;
    case 'keySaved': document.getElementById('key-area').style.display = 'none'; append('Key saved.', 'done'); break;
    case 'userPrompt': append('> ' + e.data.prompt, 'user'); vscode.postMessage({ type: 'prompt', prompt: e.data.prompt }); break;
  }
});
</script>
</body>
</html>`;
  }

  public dispose() {
    ChatPanel.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) this._disposables.pop()!.dispose();
  }
}
