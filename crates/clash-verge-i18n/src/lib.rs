use rust_i18n::i18n;
use std::borrow::Cow;
const DEFAULT_LANGUAGE: &str = "zhtw";
i18n!("locales", fallback = "zhtw");

#[inline]
pub fn current_language(language: Option<&str>) -> Cow<'static, str> {
    match language.map(|value| value.to_lowercase().replace('_', "-")) {
        Some(value) if value == "en" || value.starts_with("en-") => Cow::Borrowed("en"),
        _ => Cow::Borrowed(DEFAULT_LANGUAGE),
    }
}

#[inline]
pub const fn system_language() -> Cow<'static, str> {
    Cow::Borrowed(DEFAULT_LANGUAGE)
}

#[inline]
pub fn sync_locale(language: Option<&str>) {
    rust_i18n::set_locale(&current_language(language));
}

#[inline]
pub fn set_locale(language: &str) {
    let lang = current_language(Some(language));
    rust_i18n::set_locale(&lang);
}

#[inline]
pub fn translate(key: &str) -> Cow<'_, str> {
    rust_i18n::t!(key)
}

#[macro_export]
macro_rules! t {
    ($key:expr) => {
        $crate::translate(&$key)
    };
    ($key:expr, $($arg_name:ident = $arg_value:expr),*) => {
        {
            let mut _text = $crate::translate(&$key).into_owned();
            $(
                _text = _text.replace(&format!("{{{}}}", stringify!($arg_name)), &$arg_value);
            )*
            ::std::borrow::Cow::<'static, str>::Owned(_text)
        }
    };
}
