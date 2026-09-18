import Image from "next/image";

export default function Brand() {
  return <span className="brand-lockup">
    <span className="brand-mascot-frame"><Image className="brand-mascot" src="/capivara-header.png" width={1254} height={1254} alt="Logo Puxando a Capivara: capivara com binóculos e camisa do Brasil" unoptimized preload /></span>
    <span className="brand-wordmark"><span className="brand-first">Puxando</span><span className="brand-second">a capivara</span></span>
  </span>;
}
