import React from "react";
import ReactDOM from "react-dom/client";
import "./tailwind.css"; // Файл лежит в папке src
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("app")!).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);