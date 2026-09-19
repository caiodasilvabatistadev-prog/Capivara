import Image from "next/image";
import { useState } from "react";
import { type Politician } from "../lib/api";

const sizes = {
  compact: "h-10 w-10 rounded-lg text-sm",
  regular: "h-12 w-12 rounded-xl",
  profile: "h-28 w-24 rounded-2xl text-3xl",
};

export default function Portrait({ person, size = "regular" }: { person: Politician; size?: keyof typeof sizes }) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  return <span className={`relative grid shrink-0 place-items-center overflow-hidden bg-emerald-100 font-bold text-emerald-900 ${sizes[size]}`} title={!person.photo_url || failed ? "Foto não fornecida pela fonte oficial" : undefined}>
    {!loaded && <span aria-hidden="true">{person.name.slice(0, 1)}</span>}
    {person.photo_url && !failed && <Image className={"absolute inset-0 h-full w-full object-cover object-top " + (loaded ? "opacity-100" : "opacity-0")} src={person.photo_url} alt={"Foto de " + person.name} fill sizes={size === "profile" ? "96px" : "48px"} unoptimized onLoad={() => setLoaded(true)} onError={() => { setFailed(true); setLoaded(false); }} />}
    {(!person.photo_url || failed) && <span className="sr-only">Foto não fornecida pela fonte oficial para {person.name}</span>}
  </span>;
}
