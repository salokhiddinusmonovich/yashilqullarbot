import { FooterSocialLinks } from "@/sections/Footer/components/FooterSocialLinks";

export const FooterBottom = () => {
    return (
        <div className="box-border caret-transparent outline-[3px] no-underline">
            <div className="items-center box-border caret-transparent gap-x-4 flex flex-col-reverse justify-between max-w-screen-xl outline-[3px] gap-y-4 text-center no-underline mx-auto px-5 md:gap-x-[normal] md:flex-row md:gap-y-[normal] md:text-start md:px-8">
                <span className="box-border caret-transparent text-zinc-800 block text-[11.2px] leading-[17.92px] min-h-[auto] min-w-[auto] outline-[3px] text-center no-underline font-inter md:text-start">
                    © 2026 Yashil Qo'llar MUN.All rights reserved.
                </span>
                <FooterSocialLinks />
            </div>
        </div>
    );
};