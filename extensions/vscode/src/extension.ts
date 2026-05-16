import * as vscode from "vscode";
import * as cp from "child_process";
import * as path from "path";
import * as os from "os";

let outputChannel: vscode.OutputChannel;
let statusBar: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
  outputChannel = vscode.window.createOutputChannel("DeepSeek Code");
  statusBar = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBar.text = "$(hubot) DeepSeek";
  statusBar.tooltip = "DeepSeek Code — Click to open chat";
  statusBar.command = "deepseek-code.openChat";
  statusBar.show();
  context.subscriptions.push(statusBar);

  // Open chat panel
  context.subscriptions.push(
    vscode.commands.registerCommand("deepseek-code.openChat", () => {
      ChatPanel.createOrShow(context.extensionUri);
    })
  );

  // Explain selected code
  context.subscriptions.push(
    vscode.commands.registerCommand("deepseek-code.explainCode", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.document.getText(editor.selection);
      if (!selection) {
        vscode.window.showWarningMessage("Select some code first.");
        return;
      }
      const panel = ChatPanel.createOrShow(context.extensionUri);
      panel.sendPrompt(`Explain this code:\n\`\`\`\n${selection}\n\`\`\``);
    })
  );

  // Fix selected code
  context.subscriptions.push(
    vscode.commands.registerCommand("deepseek-code.fixCode", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.document.getText(editor.selection);
      if (!selection) {
        vscode.window.showWarningMessage("Select some code first.");
        return;
      }
      const panel = ChatPanel.createOrShow(context.extensionUri);
      panel.sendPrompt(
        `Fix issues in this code. Find bugs, edge cases, security problems:\n\`\`\`\n${selection}\n\`\`\``
      );
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

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this._panel = panel;
    this._cliPath = this._findCli();
    this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    this._panel.webview.onDidReceiveMessage(
      this._handleMessage.bind(this),
      null,
      this._disposables
    );
  }

  public static createOrShow(extensionUri: vscode.Uri): ChatPanel {
    if (ChatPanel.currentPanel) {
      ChatPanel.currentPanel._panel.reveal(vscode.ViewColumn.Beside);
      return ChatPanel.currentPanel;
    }
    const panel = vscode.window.createWebviewPanel(
      "deepseek-code",
      "DeepSeek Code",
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [extensionUri],
      }
    );
    ChatPanel.currentPanel = new ChatPanel(panel, extensionUri);
    return ChatPanel.currentPanel;
  }

  public sendPrompt(prompt: string) {
    this._panel.webview.postMessage({ type: "userPrompt", prompt });
  }

  private _findCli(): string {
    // Find deepseek CLI in common locations
    const candidates = [
      path.join(os.homedir(), ".local", "bin", "deepseek"),
      path.join(os.homedir(), ".venv", "Scripts", "deepseek.exe"),
      "deepseek",
    ];
    for (const c of candidates) {
      try {
        cp.execSync(`"${c}" --help`, { timeout: 3000, stdio: "ignore" });
        return c;
      } catch {
        continue;
      }
    }
    return "deepseek"; // fallback to PATH
  }

  private async _handleMessage(message: any) {
    switch (message.type) {
      case "prompt":
        await this._runCli(message.prompt);
        break;
    }
  }

  private async _runCli(prompt: string) {
    this._panel.webview.postMessage({ type: "thinking", text: "..." });

    try {
      const child = cp.spawn(this._cliPath, ["chat", "-p", prompt], {
        env: { ...process.env },
        stdio: ["pipe", "pipe", "pipe"],
      });

      child.stdout.on("data", (data: Buffer) => {
        const text = data.toString("utf-8");
        this._panel.webview.postMessage({ type: "response", text });
      });

      child.stderr.on("data", (data: Buffer) => {
        this._panel.webview.postMessage({
          type: "error",
          text: data.toString("utf-8"),
        });
      });

      child.on("close", (code) => {
        this._panel.webview.postMessage({ type: "done", code });
      });

      child.stdin.write(prompt + "\n");
      child.stdin.end();
    } catch (e: any) {
      this._panel.webview.postMessage({
        type: "error",
        text: `Failed to run deepseek CLI: ${e.message}`,
      });
    }
  }

  private _getHtml(
    webview: vscode.Webview,
    extensionUri: vscode.Uri
  ): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DeepSeek Code</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      color: var(--vscode-foreground);
      background: var(--vscode-sideBar-background);
      padding: 12px;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    #output {
      flex: 1;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
      margin-bottom: 8px;
    }
    #input-row { display: flex; gap: 8px; }
    #input {
      flex: 1;
      background: var(--vscode-input-background);
      color: var(--vscode-input-foreground);
      border: 1px solid var(--vscode-input-border);
      padding: 8px;
      font-family: inherit;
      font-size: inherit;
      resize: none;
    }
    #input:focus { outline: 1px solid var(--vscode-focusBorder); }
    #send {
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: none;
      padding: 8px 16px;
      cursor: pointer;
      font-size: inherit;
    }
    #send:hover { background: var(--vscode-button-hoverBackground); }
    .thinking { color: var(--vscode-descriptionForeground); font-style: italic; }
    .error { color: var(--vscode-errorForeground); }
    .done { color: var(--vscode-descriptionForeground); font-size: 0.85em; margin-top: 4px; }
    .user { color: var(--vscode-textLink-foreground); margin-bottom: 8px; }
    .assistant { margin-bottom: 12px; }
  </style>
</head>
<body>
  <div id="output"></div>
  <div id="input-row">
    <textarea id="input" rows="2" placeholder="Ask DeepSeek Code... (Shift+Enter for newline, Enter to send)"></textarea>
    <button id="send">Send</button>
  </div>
  <script>
    const vscode = acquireVsCodeApi();
    const output = document.getElementById('output');
    const input = document.getElementById('input');
    const send = document.getElementById('send');

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

    send.addEventListener('click', sendPrompt);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendPrompt();
      }
    });

    window.addEventListener('message', (e) => {
      const msg = e.data;
      switch (msg.type) {
        case 'response': append(msg.text, 'assistant'); break;
        case 'thinking': append(msg.text, 'thinking'); break;
        case 'error': append(msg.text, 'error'); break;
        case 'done': append('— done —', 'done'); break;
        case 'userPrompt':
          append('> ' + msg.prompt, 'user');
          vscode.postMessage({ type: 'prompt', prompt: msg.prompt });
          break;
      }
    });
  </script>
</body>
</html>`;
  }

  public dispose() {
    ChatPanel.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) {
      this._disposables.pop()!.dispose();
    }
  }
}
