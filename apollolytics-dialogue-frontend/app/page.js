// app/page.js
"use client";
import Link from "next/link";
import styles from "./Home.module.css"; // Reuse existing styles or create new ones

export default function Home() {
  return (
    <div className={styles.container}>
      <h1 className={styles.header}>Welcome to Apollolytics</h1>
      <div className={styles.linksContainer}>
        <Link href="/production" className={styles.linkButton}>
          Go to Production
        </Link>
        <Link href="/experiment" className={styles.linkButton}>
          Go to Experiment
        </Link>
      </div>
    </div>
  );
}
