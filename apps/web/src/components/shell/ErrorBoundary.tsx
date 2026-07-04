import { Component } from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
            padding: "24px",
            background: "#f6f7fa",
            color: "#162033",
            fontFamily: '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif',
            textAlign: "center",
          }}
        >
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 24,
              background: "rgba(161, 67, 67, 0.1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 24,
              marginBottom: 16,
            }}
          >
            ⚠
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 8px" }}>页面出现意外错误</h1>
          <p style={{ fontSize: 14, color: "#4a5568", margin: "0 0 24px", lineHeight: 1.6, maxWidth: 480 }}>
            系统遇到一个意外问题，请尝试重新加载。如果问题持续存在，请联系维护人员。
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              padding: "10px 24px",
              border: "none",
              borderRadius: 12,
              background: "#4f56d1",
              color: "#fff",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              marginBottom: 24,
            }}
          >
            重新加载
          </button>
          {this.state.error && (
            <details style={{ fontSize: 11, color: "#8c97aa", maxWidth: 480, textAlign: "left" }}>
              <summary style={{ cursor: "pointer" }}>错误详情</summary>
              <pre style={{ marginTop: 8, padding: 12, background: "#f0f0f0", borderRadius: 8, overflowX: "auto", whiteSpace: "pre-wrap" }}>
                {this.state.error.toString()}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
