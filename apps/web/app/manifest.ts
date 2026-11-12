import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest {
  return { name:"WIDAL-SCAN AI — Wireless Edition", short_name:"WIDAL-SCAN", description:"AI-assisted Widal imaging prototype", start_url:"/", display:"standalone", background_color:"#f4f7fb", theme_color:"#102b46", icons:[] };
}