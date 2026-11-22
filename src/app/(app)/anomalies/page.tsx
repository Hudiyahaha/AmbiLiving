import { redirect } from "next/navigation";

// Routine deviations are the Monitoring alerts tab.
export default function Page() {
  redirect("/monitoring?tab=alerts");
}
