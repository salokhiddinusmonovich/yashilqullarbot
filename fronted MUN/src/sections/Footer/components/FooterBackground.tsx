export type FooterBackgroundProps = {
    backgroundVariant: string;
};

export const FooterBackground = (props: FooterBackgroundProps) => {
    return (
        <div
            className={`box-border caret-transparent outline-[3px] no-underline ${props.backgroundVariant}`}
        ></div>
    );
};