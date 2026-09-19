import "./globals.css";
export const metadata = { title: "Puxando a Capivara | Consulta Pública", description: "Consulte autoridades, governadores e candidaturas em fontes oficiais e entenda como a política funciona", icons: { icon: "/logo.png", apple: "/logo.png" } };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
