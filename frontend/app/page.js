// app/page.js
"use client";
import Link from "next/link";
import styles from "./Home.module.css"; // Ensure this CSS module exists and is styled appropriately

export default function Home() {
  return (
    <div className={styles.container}>
      <h1 className={styles.header}>Welcome to Apollolytics</h1>
      <div className={styles.linksContainer}>
        <Link href="/production_positive" className={styles.linkButton}>
          Go to Production Positive
        </Link>
        <Link href="/production_negative" className={styles.linkButton}>
          Go to Production Negative
        </Link>
        <Link href="/experiment_positive" className={styles.linkButton}>
          Go to Experiment Positive
        </Link>
        <Link href="/experiment_negative" className={styles.linkButton}>
          Go to Experiment Negative
        </Link>
      </div>
    </div>
  );
}
