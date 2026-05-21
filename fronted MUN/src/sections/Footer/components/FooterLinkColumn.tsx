export type FooterLinkColumnProps = {
    title: string;
    links: {
        href: string;
        label: string;
    }[];
};

export const FooterLinkColumn = (props: FooterLinkColumnProps) => {
    return (
        <div className="box-border caret-transparent gap-x-4 flex flex-col min-h-[auto] min-w-[auto] outline-[3px] gap-y-4 no-underline">
            <span className="box-border caret-transparent text-emerald-500 block text-[9.6px] font-extrabold tracking-[2.112px] leading-[15.36px] min-h-[auto] min-w-[auto] outline-[3px] no-underline uppercase mb-[4.8px] font-montserrat">
                {props.title}
            </span>
            {props.links.map((link) => (
                <a
                    key={`${link.href}-${link.label}`}
                    href={link.href}
                    className="box-border caret-transparent text-neutral-600 block text-[13.12px] leading-[20.992px] min-h-[auto] min-w-[auto] outline-[3px] no-underline hover:text-white/80 hover:border-white/80"
                >
                    {link.label}
                </a>
            ))}
        </div>
    );
};