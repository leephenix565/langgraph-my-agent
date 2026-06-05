import {
  checkpointerStatusLabel,
  continuityLabel,
  overallStatusLabel,
  readinessStatusLabel,
  storeLabel,
  zhCN,
} from "../content/zh-CN";
import type { HealthResponse } from "../types/chat";

interface SettingsPageProps {
  health: HealthResponse | null;
  isLoading: boolean;
  unavailable: boolean;
}

function statusTone(status: string) {
  if (status === "ready" || status === "configured" || status === "enabled") {
    return "ready";
  }
  if (status === "disabled") {
    return "neutral";
  }
  return "warning";
}

function describeRuntime(health: HealthResponse) {
  return health.runtime.status === "ready"
    ? "运行时可用，当前可以继续处理聊天请求。"
    : "运行时正在检查中，系统暂时无法保证完整的对话处理能力。";
}

function describeProvider(health: HealthResponse) {
  if (health.providerEnv.status === "configured") {
    return "高级模型连接已配置，可用于后续需要模型服务的路径。";
  }
  if (health.providerEnv.status === "unknown") {
    return "当前尚未确认高级模型连接状态，请结合运行时状态一并查看。";
  }
  return "高级模型连接未启用；当前本地固定流程仍可使用。";
}

function describeSearch(health: HealthResponse) {
  return health.searchEnv.status === "configured"
    ? "资料检索连接已配置，可用于后续补充公开信息。"
    : "资料检索连接未启用；当前本地固定流程仍可使用。";
}

function describeCheckpointer(health: HealthResponse) {
  if (health.checkpointer.status === "enabled") {
    return "持久化连续性已启用，系统可以优先使用持久线程路径。";
  }
  if (health.checkpointer.status === "disabled") {
    return "当前使用回放连续性，适合本地演示和只读审计。";
  }
  return "已请求持久化连续性，但当前未能成功启用。";
}

function continuityDescription(health: HealthResponse) {
  return health.continuityDefault === "persistent"
    ? zhCN.settings.continuityPersistentBody
    : zhCN.settings.continuityReplayBody;
}

function renderSurfaceCard(
  title: string,
  value: string,
  tone: string,
  description: string,
  extra?: import("react").ReactNode,
) {
  return (
    <section className="settings-card">
      <div className="settings-card__head">
        <span className="settings-card__label">{title}</span>
        <span className={`settings-pill settings-pill--${tone}`}>{value}</span>
      </div>
      <p>{description}</p>
      {extra ? <div className="settings-card__meta">{extra}</div> : null}
    </section>
  );
}

export function SettingsPage({ health, isLoading, unavailable }: SettingsPageProps) {
  if (unavailable) {
    return (
      <div className="page page--settings">
        <header className="settings-header">
          <div className="settings-header__copy">
            <span className="settings-header__eyebrow">{zhCN.settings.eyebrow}</span>
            <h1>{zhCN.settings.title}</h1>
            <p>{zhCN.settings.description}</p>
          </div>
        </header>
        <section className="thread-notice thread-notice--unavailable" aria-label="系统状态不可用提示">
          <strong>{zhCN.settings.unavailableTitle}</strong>
          <p>{zhCN.settings.unavailableBody}</p>
        </section>
      </div>
    );
  }

  if (isLoading && !health) {
    return (
      <div className="page page--settings">
        <header className="settings-header">
          <div className="settings-header__copy">
            <span className="settings-header__eyebrow">{zhCN.settings.eyebrow}</span>
            <h1>{zhCN.settings.title}</h1>
            <p>{zhCN.settings.description}</p>
          </div>
        </header>
        <section className="thread-notice" aria-label="系统状态加载中">
          <strong>{zhCN.settings.loadingTitle}</strong>
          <p>{zhCN.settings.loadingBody}</p>
        </section>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="page page--settings">
        <header className="settings-header">
          <div className="settings-header__copy">
            <span className="settings-header__eyebrow">{zhCN.settings.eyebrow}</span>
            <h1>{zhCN.settings.title}</h1>
            <p>{zhCN.settings.description}</p>
          </div>
        </header>
      </div>
    );
  }

  return (
    <div className="page page--settings">
      <header className="settings-header">
        <div className="settings-header__copy">
          <span className="settings-header__eyebrow">{zhCN.settings.eyebrow}</span>
          <h1>{zhCN.settings.title}</h1>
          <p>{zhCN.settings.description}</p>
        </div>
      </header>

      <section className="settings-summary" aria-label="系统总体状态">
        <div className="settings-summary__lead">
          <span className="settings-card__label">{zhCN.settings.overallTitle}</span>
          <strong>{overallStatusLabel(health.overallStatus)}</strong>
          <p>
            {health.overallStatus === "ready"
              ? "当前公共适配器已连接，核心运行能力处于可用状态。"
              : "当前基础功能可用，高级连接状态可在下方诊断中查看。"}
          </p>
        </div>

        <div className="settings-summary__facts">
          <div className="settings-fact">
            <span>{zhCN.settings.continuityTitle}</span>
            <strong>{continuityLabel(health.continuityDefault)}</strong>
            <small>{continuityDescription(health)}</small>
          </div>
          <div className="settings-fact">
            <span>{zhCN.settings.storeTitle}</span>
            <strong>{storeLabel(health.store)}</strong>
            <small>当前 public store 以文件形式保存公开线程数据。</small>
          </div>
        </div>
      </section>

      <div className="settings-grid">
        {renderSurfaceCard(
          zhCN.settings.runtimeTitle,
          readinessStatusLabel(health.runtime.status),
          statusTone(health.runtime.status),
          describeRuntime(health),
        )}
      </div>

      <details className="settings-advanced">
        <summary>{zhCN.settings.advancedDiagnostics}</summary>
        <p>{zhCN.settings.advancedDiagnosticsBody}</p>
        <div className="settings-grid">
          {renderSurfaceCard(
            zhCN.settings.providerTitle,
            readinessStatusLabel(health.providerEnv.status),
            statusTone(health.providerEnv.status),
            describeProvider(health),
          )}
          {renderSurfaceCard(
            zhCN.settings.searchTitle,
            readinessStatusLabel(health.searchEnv.status),
            statusTone(health.searchEnv.status),
            describeSearch(health),
          )}
          {renderSurfaceCard(
            zhCN.settings.checkpointerTitle,
            checkpointerStatusLabel(health.checkpointer.status),
            statusTone(health.checkpointer.status),
            describeCheckpointer(health),
            <>
              <span>{zhCN.settings.modeLabel}</span>
              <strong>{health.checkpointer.mode}</strong>
            </>,
          )}
        </div>
      </details>
    </div>
  );
}
