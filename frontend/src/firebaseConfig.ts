// src/firebaseConfig.ts
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyD4Ig5SbiJeJxldhoAYBG7a-teifSq_3Mc",
  authDomain: "ai-education-app-9d7ae.firebaseapp.com",
  projectId: "ai-education-app-9d7ae",
  storageBucket: "ai-education-app-9d7ae.firebasestorage.app",
  messagingSenderId: "626071618319",
  appId: "1:626071618319:web:034c166a27f28fd5bcb47a",
  measurementId: "G-3PL94QK95K"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
;(window as any).auth = auth;