import { useState } from "react";
import { NavbarBrand } from "@/sections/Navbar/components/NavbarBrand";
import { SocialLinks } from "@/sections/Navbar/components/SocialLinks";
import { DesktopNav } from "@/sections/Navbar/components/DesktopNav";
import { DesktopActions } from "@/sections/Navbar/components/DesktopActions";
import { MobileActions } from "@/sections/Navbar/components/MobileActions";
import { MobileMenu } from "@/sections/Navbar/components/MobileMenu";



export const Navbar = () => {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <header className="box-border caret-transparent outline-[3px] fixed no-underline w-full z-[1000] left-0 top-0">
        <div className="items-center backdrop-blur-[20px] bg-gray-950/100 box-border caret-transparent gap-x-0 flex h-14 justify-between outline-[3px] gap-y-0 no-underline px-[17.6px] border-t-white border-b-white/10 border-x-white border-b md:bg-zinc-950/60 md:gap-x-8 md:h-16 md:justify-normal md:gap-y-8 md:px-10 md:border-b-white/0">
          <NavbarBrand />
          <SocialLinks />
          <DesktopNav />
          <DesktopActions />
          <MobileActions
            open={mobileOpen}
            onToggle={() => setMobileOpen(!mobileOpen)}
          />
        </div>
        {mobileOpen && <MobileMenu onClose={() => setMobileOpen(false)} />}
      </header>
    </>
  );
};