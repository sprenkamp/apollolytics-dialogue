"use client";
import Link from "next/link";

export default function Home() {
  return (
    <div style={containerStyle}>
      <h1 style={headerStyle}>Welcome to Apollolytics</h1>
      <div style={linksContainerStyle}>
        <Link href="/production_positive" style={linkButtonStyle}>
          Go to Production Positive
        </Link>
        <Link href="/production_negative" style={linkButtonStyle}>
          Go to Production Negative
        </Link>
        <Link href="/experiment_positive" style={linkButtonStyle}>
          Go to Experiment Positive
        </Link>
        <Link href="/experiment_negative" style={linkButtonStyle}>
          Go to Experiment Negative
        </Link>
      </div>
    </div>
  );
}

const containerStyle = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  height: "100vh",
  backgroundColor: "#f5f7fa",
  fontFamily: "'Arial', sans-serif",
};

const headerStyle = {
  fontSize: "2.5rem",
  marginBottom: "20px",
  color: "#333",
};

const linksContainerStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(2, 1fr)",
  gap: "20px",
  width: "80%",
  maxWidth: "600px",
};

const linkButtonStyle = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "15px",
  borderRadius: "10px",
  textDecoration: "none",
  fontWeight: "bold",
  fontSize: "1.2rem",
  color: "#fff",
  backgroundColor: "#0070f3",
  transition: "background-color 0.3s, transform 0.3s",
  textAlign: "center",
};

linkButtonStyle["&:hover"] = {
  backgroundColor: "#005bb5",
  transform: "translateY(-3px)",
};

linkButtonStyle["&:active"] = {
  backgroundColor: "#003d80",
  transform: "translateY(0)",
};
