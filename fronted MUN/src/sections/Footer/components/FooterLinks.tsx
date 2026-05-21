import { FooterLinkColumn } from "@/sections/Footer/components/FooterLinkColumn";

export const FooterLinks = () => {
    return (
        <nav
            aria-label="Footer navigation"
            className="box-border caret-transparent gap-x-10 flex min-h-[auto] min-w-[auto] outline-[3px] gap-y-10 no-underline"
        >
            <FooterLinkColumn
                title="Conference"
                links={[
                    { href: "/about", label: "About" },
                    { href: "/committees", label: "Committees" },
                    { href: "/schedule", label: "Schedule" },
                    { href: "/sponsors", label: "Partners" },
                ]}
            />
            <FooterLinkColumn
                title="Participate"
                links={[
                    { href: "/team", label: "Team" },
                    { href: "/registration", label: "Register" },
                    { href: "/contact", label: "Contact" },
                ]}
            />
        </nav>
    );
};