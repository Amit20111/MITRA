import { notFound } from "next/navigation";
import { Workspace } from "@/components/workspace";
export default async function Page({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (!["tasks", "memory", "settings", "chat"].includes(section)) notFound();
  return (
    <Workspace
      initialView={
        section === "chat"
          ? "workspace"
          : (section as "tasks" | "memory" | "settings")
      }
    />
  );
}
