import "./globals.css";
export const metadata = { title: "Puxando a Capivara | Consulta Pública", description: "Consulte dados oficiais dos três poderes no âmbito federal", icons: { icon: "/logo.png", apple: "/logo.png" } };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
