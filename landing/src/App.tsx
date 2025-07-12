import React from "react";

export default function App() {
  return (
    <main style={{ padding: "4rem", fontFamily: "sans-serif", textAlign: "center" }}>
      <h1 style={{ fontSize: "2rem" }}>📬 ColdCraft</h1>
      <p style={{ fontSize: "1.1rem" }}>
        Generate hyper-personalized cold email openers in seconds.
      </p>

      <a
        href="https://coldcraft-app-eubqfeupsu3c3ickgej6cb.streamlit.app/"
        target="_blank"
        rel="noopener noreferrer"
      >
        <button style={{ marginTop: "1rem", padding: "0.5rem 1rem", fontSize: "1rem" }}>
          Try It Now
        </button>
      </a>
    </main>
  );
}
