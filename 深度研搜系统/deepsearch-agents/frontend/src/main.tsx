import "antd/dist/reset.css";
import { App as AntApp, ConfigProvider, theme } from "antd";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#5b5bd6",
          colorSuccess: "#12b76a",
          colorWarning: "#f79009",
          colorError: "#f04438",
          colorInfo: "#5b5bd6",
          colorBgBase: "#ffffff",
          colorBgContainer: "#ffffff",
          colorBorder: "#e8eaed",
          borderRadius: 10,
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif",
          fontFamilyCode:
            "'JetBrains Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', monospace"
        },
        components: {
          Button: {
            controlHeightLG: 44,
            primaryShadow: "0 4px 14px rgba(91, 91, 214, 0.25)"
          },
          Input: {
            activeBorderColor: "#5b5bd6",
            hoverBorderColor: "#8b5cf6"
          }
        }
      }}
    >
      <AntApp>
        <App />
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>
);
