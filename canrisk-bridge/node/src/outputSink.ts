import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';

export const CANRISK_UPLOAD_URL = 'https://canrisk.org';

export interface BrowserLauncher {
  open(url: string): void;
}

/** Opens URLs using the OS default browser. */
export class PlatformBrowserLauncher implements BrowserLauncher {
  open(url: string): void {
    const { command, args } = launchCommand(url);
    const child = spawn(command, args, { stdio: 'ignore', detached: true });
    child.unref();
  }
}

export interface OutputSinkOptions {
  readonly outputDir: string;
  readonly browser: BrowserLauncher;
}

export class OutputSink {
  private readonly outputDir: string;
  private readonly browser: BrowserLauncher;

  constructor(options: OutputSinkOptions) {
    this.outputDir = options.outputDir;
    this.browser = options.browser;
  }

  save(pedigreeId: string, payload: string): string {
    mkdirSync(this.outputDir, { recursive: true });
    const path = resolve(this.outputDir, filenameFor(pedigreeId));
    writeFileSync(path, payload, 'utf8');
    return path;
  }

  openUploadPage(): void {
    this.browser.open(CANRISK_UPLOAD_URL);
  }
}

export function filenameFor(pedigreeId: string): string {
  return `evagene-canrisk-${pedigreeId.slice(0, 8)}.txt`;
}

function launchCommand(url: string): { command: string; args: readonly string[] } {
  switch (process.platform) {
    case 'win32':
      return { command: 'cmd', args: ['/c', 'start', '""', url] };
    case 'darwin':
      return { command: 'open', args: [url] };
    default:
      return { command: 'xdg-open', args: [url] };
  }
}
