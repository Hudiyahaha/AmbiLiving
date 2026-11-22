import { redirect } from "next/navigation";

// Activities are a Monitoring tab.
export default function Page() {
  redirect("/monitoring?tab=activities");
}
