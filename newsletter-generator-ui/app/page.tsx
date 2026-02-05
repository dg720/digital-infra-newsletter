import dynamic from "next/dynamic"

const HomeClient = dynamic(() => import("@/components/home-client"), {
  ssr: false,
})

export default function Home() {
  return <HomeClient />
}
