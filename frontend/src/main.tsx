import React from "react";
import ReactDOM from "react-dom/client";
import "maplibre-gl/dist/maplibre-gl.css";
import "./index.css";
import { App } from "./App";
import { LaunchIntro } from "./LaunchIntro";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /><LaunchIntro /></React.StrictMode>
);
