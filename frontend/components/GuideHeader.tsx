"use client";
import { useRouter } from "next/navigation";
import Header from "./Header";
export default function GuideHeader() {
  const router = useRouter();
  return <Header onNavigate={section => router.push(section === "consulta" ? "/#public-search" : "/#" + section)} />;
}
