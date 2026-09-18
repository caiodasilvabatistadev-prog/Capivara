import Image from "next/image";
import { useState } from "react";
import { type Politician } from "../lib/api";

export default function Portrait({ person }: { person: Politician }) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  return <span className="relative grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-xl bg-emerald-100 font-bold text-emerald-900">
    {!loaded && <span aria-hidden="true">{person.name.slice(0, 1)}</span>}
    {person.photo_url && !failed && <Image className={"absolute inset-0 h-12 w-12 object-cover object-top " + (loaded ? "opacity-100" : "opacity-0")} src={person.photo_url} alt={"Foto de " + person.name} width={48} height={48} unoptimized onLoad={() => setLoaded(true)} onError={() => { setFailed(true); setLoaded(false); }} />}
  </span>;
}
