import { CommandPalette } from "@/components/shell/command-palette";
import { Rail } from "@/components/shell/rail";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg text-text">
      <Rail />
      <CommandPalette />
      <main className="min-h-screen pl-[76px] md:pl-[220px]">
        <div className="mx-auto w-full max-w-[1440px] px-4 py-5 md:px-8 md:py-8">{children}</div>
      </main>
    </div>
  );
}
