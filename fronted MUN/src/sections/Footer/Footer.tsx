import { FooterBackground } from "@/sections/Footer/components/FooterBackground";
import { FooterContent } from "@/sections/Footer/components/FooterContent";
import { FooterBottom } from "@/sections/Footer/components/FooterBottom";
import { FooterCredit } from "@/sections/Footer/components/FooterCredit";

export const Footer = () => {
    return (
        <footer className="bg-neutral-900 box-border caret-transparent outline-[3px] relative no-underline z-[1] overflow-hidden mt-12 pt-10 pb-8">
            <FooterBackground backgroundVariant="bg-[radial-gradient(rgba(255,102,0,0.05)_0%,rgba(0,0,0,0)_70%)] blur-2xl h-[220px] pointer-events-none absolute translate-x-[-50.0%] w-[500px] z-0 left-2/4 top-0" />
            <FooterBackground backgroundVariant="hidden" />
            <FooterContent />
            <FooterBottom />
            <FooterCredit />
        </footer>
    );
};