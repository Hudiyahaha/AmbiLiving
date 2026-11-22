import { redirect } from "next/navigation";

// Scenario replay is now Past days.
export default function Page() {
  redirect("/days");
}
