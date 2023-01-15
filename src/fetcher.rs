use std::fs;
use std::path::Path;
use url::Url;
use icalendar::{Calendar, parser};
use sha2::{Sha256, Digest};
use sha2::digest::FixedOutput;
#[cfg(not(test))]
use log::{debug, info, warn};
#[cfg(test)]
use std::{println as debug, println as warn, println as info};

#[derive(Debug)]
pub struct Remote {
    location: Location,
}

#[derive(Debug)]
pub enum Location {
    Online(Url),
    Local(Box<Path>),
}


impl Remote {

    pub fn new(location: &str) -> Remote {
        let location = match Url::parse(location) {
            Ok(url) => Location::Online(url),
            Err(_) => Location::Local(Box::from(Path::new(location)))
        };

        Remote {location}
    }

    pub fn is_local(&self) -> bool {
        match &self.location {
            Location::Online(_) => false,
            Location::Local(_) => true,
        }
    }

    pub fn hash(&self) -> String {
        let path = match &self.location {
            Location::Online(url) => url.to_string(),
            Location::Local(path) => String::from(path.to_str().unwrap_or("")),
        };

        let mut hasher = Sha256::new();
        hasher.update(path);

        format!("{:x}", hasher.finalize_fixed())
    }

    pub fn get(&self) -> Option<Calendar> {
        debug!("Getting ics from {:?}", self.location);
        let content = match &self.location {
            Location::Online(url) => {
                match get_url_content(url.to_string()) {
                    Ok(content) => Some(content),
                    Err(_) => None,
                }
            }

            Location::Local(path) => {
                match fs::read_to_string(path) {
                    Ok(content) => Some(content),
                    Err(_) => None,
                }
            }
        };

        if let Some(content) = content {
            if let Ok(cal) = parser::read_calendar(&content) {
                return Some(Calendar::from(cal));
            }
        }

        None
    }


}



fn get_url_content(url: String) -> Result<String, reqwest::Error> {
    let content = reqwest::blocking::get(url)?
        .text()?;

    Ok(content)
}



#[cfg(test)]
mod test {
    use std::path::Path;
    use super::*;

    #[test]
    fn get_ics_from_file() {

        let remote = Remote{
            location: Location::Local(Box::from(Path::new("resources/test/belgium.ics"))),
        };

        let cal = remote.get();

        assert!(cal.is_some());

        let cal = cal.unwrap();

        // Calendar has 40 events
        assert_eq!(cal.len(), 40);
        assert_eq!(cal.get_name().unwrap(), "Belgium Holidays");
    }

    #[test]
    fn cannot_parse_calendar() {

        let remote = Remote {
            location: Location::Online(Url::parse("https://example.com/").unwrap()),
        };

        let cal = remote.get();

        if let Some(cal) = cal {
            assert_eq!(cal.len(), 0);
        }
    }

    #[test]
    fn hash_test() {
        let remote = Remote {
            location: Location::Local(Box::from(Path::new("file.ics"))),
        };

        let remote1 = Remote {
            location: Location::Local(Box::from(Path::new("file.ics"))),
        };

        assert_eq!(remote.hash(), remote1.hash())
    }
}