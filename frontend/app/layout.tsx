import "./globals.css";
export const metadata = { title: "Consulta Pública", description: "Consulte dados oficiais de deputados federais" };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
