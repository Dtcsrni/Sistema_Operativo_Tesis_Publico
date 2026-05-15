import fs from 'fs';
import os from 'os';
import path from 'path';

interface OpenClawConfigFile {
  gateway?: {
    token?: string;
    url?: string;
    gatewayUrl?: string;
    gateway_url?: string;
  };
  token?: string;
  url?: string;
  gatewayUrl?: string;
  gateway_url?: string;
}

const DEFAULT_GATEWAY_URL = 'http://127.0.0.1:18789';
const DEFAULT_CONFIG_PATH = path.join(os.homedir(), '.openclaw', 'openclaw.json');

let cachedFileConfig: OpenClawConfigFile | null | undefined;

function getConfigPath(): string {
  return process.env.OPENCLAW_CONFIG_PATH || DEFAULT_CONFIG_PATH;
}

function readConfigFile(): OpenClawConfigFile | null {
  if (cachedFileConfig !== undefined) {
    return cachedFileConfig;
  }

  const configPath = getConfigPath();

  try {
    if (!fs.existsSync(configPath)) {
      cachedFileConfig = null;
      return null;
    }

    const raw = fs.readFileSync(configPath, 'utf8');
    const parsed = JSON.parse(raw) as OpenClawConfigFile;
    cachedFileConfig = parsed;
    return parsed;
  } catch {
    cachedFileConfig = null;
    return null;
  }
}

function pickFirstString(...values: Array<string | undefined | null>): string {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return '';
}

export function getOpenClawGatewayUrl(): string {
  const config = readConfigFile();
  const rawUrl = pickFirstString(
    process.env.OPENCLAW_GATEWAY_URL,
    config?.gateway?.url,
    config?.gateway?.gatewayUrl,
    config?.gateway?.gateway_url,
    config?.url,
    config?.gatewayUrl,
    config?.gateway_url,
    DEFAULT_GATEWAY_URL,
  );
  return rawUrl.replace(/^http:\/\//, 'ws://').replace(/^https:\/\//, 'wss://');
}

export function getOpenClawGatewayToken(): string {
  const config = readConfigFile();
  return pickFirstString(
    process.env.OPENCLAW_GATEWAY_TOKEN,
    config?.gateway?.token,
    config?.token,
  );
}
