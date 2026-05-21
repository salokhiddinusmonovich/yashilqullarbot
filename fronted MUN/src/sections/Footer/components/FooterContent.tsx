import { FooterBrand } from "@/sections/Footer/components/FooterBrand";
import { FooterLinks } from "@/sections/Footer/components/FooterLinks";
import { FooterContact } from "@/sections/Footer/components/FooterContact";

export const FooterContent = () => {
    return (
        <div className="items-start box-border caret-transparent gap-x-10 grid grid-cols-[1fr] max-w-screen-xl outline-[3px] relative gap-y-10 no-underline z-[1] mx-auto px-5 md:gap-x-24 md:grid-cols-[1.6fr_1fr_1.4fr] md:gap-y-24 md:px-8">
            <FooterBrand />
            <FooterLinks />
            <FooterContact />
        </div>
    );
};