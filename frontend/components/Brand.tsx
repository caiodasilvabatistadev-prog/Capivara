import Image from "next/image";


export default function Brand() {
  return <div className="flex min-w-0 items-center gap-3">
    <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-2xl border bg-white sm:h-20 sm:w-20" style={{ background: "white" }}>
      <Image src="/logo.png" width={1408} height={768} alt="Logo Puxando a Capivara: capivara com binóculos e camisa do Brasil" unoptimized preload style={{ position: "absolute", width: "380%", maxWidth: "none", height: "auto", left: "-140%", top: "-30%" }} />
    </div>
    <div className="min-w-0"><p className="text-lg font-bold sm:text-xl">Puxando a Capivara</p><p className="mt-1 max-w-64 text-xs leading-relaxed text-slate-500">Transparência para acompanhar o poder público</p></div>
  </div>;
}

