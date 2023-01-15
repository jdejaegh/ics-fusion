use chrono::{DateTime, Utc};
use icalendar::{Calendar, parser};
use rusqlite::{Connection, Error, params, Rows, Statement};
#[cfg(not(test))]
use log::{debug, info, warn};
#[cfg(test)]
use std::{println as debug, println as warn, println as info};


use crate::fetcher::{Remote};

struct CacheEntry {
    hash: String,
    update_time: Option<String>,
    calendar: Option<String>,
}

pub struct CachedRemote {
    cache_delay: Option<u32>,
    remote: Remote,
    cache_db: Connection,
}

impl CachedRemote {
    pub fn cache(&self) -> Result<(), Error> {
        debug!("Start caching of {:?}", self.remote);
        if self.cache_delay.is_none() || self.remote.is_local() {
            debug!("No need to cache {:?}", self.remote);
            return Ok(());
        }

        self.force_cache()
    }

    pub fn force_cache(&self) -> Result<(), Error> {
        let entry = CacheEntry {
            hash: self.remote.hash(),
            update_time: Some(Utc::now().to_rfc3339()),
            calendar: match self.remote.get() {
                Some(cal) => Some(parser::unfold(&cal.to_string())),
                None => None,
            },
        };

        self.cache_db.execute("REPLACE INTO cache (hash, update_time, calendar) values (?1, ?2, ?3);",
                              params![&entry.hash, &entry.update_time, &entry.calendar])?;
        debug!("Cached {:?}", self.remote);
        Ok(())
    }

    pub fn get_from_cache(&self) -> Option<Calendar> {
        info!("Getting {:?} from cache", self.remote);
        let mut statement: Statement;

        if let Ok(stmt) = self.cache_db.prepare("SELECT calendar FROM cache where hash = ?"){
            statement = stmt;
        } else {
            warn!("Could not prepare statement");
            return None;
        }

        let mut rows: Rows;
        if let Ok(rows_ok) = statement.query([self.remote.hash()]) {
            rows = rows_ok;
        } else {
            warn!("Could not get a row from the query");
            return None;
        }

        let cal_str: String;
        if let Ok(Some(r)) = rows.next(){
            if let Ok(s) = r.get(0) {
                cal_str = s;
            } else {
                return None
            }
        } else {
            warn!("No result from query");
            return None;
        }

        if let Ok(cal) = parser::read_calendar(&cal_str) {
            debug!("Returned cached from {:?}", self.remote);
            debug!("{}", cal);
            return Some(Calendar::from(cal));
        }

        warn!("Unable to parse calendar from cache");
        None
    }

    pub fn get(&self) -> Option<Calendar> {
        if self.cache_delay.is_none() || self.remote.is_local() {
            return self.remote.get();
        }

        if let Some(cal) = self.get_from_cache() {
            return Some(cal);
        }

        self.remote.get()
    }

}


fn create_cache(path: Option<String>) -> Result<Connection, Error> {
    let conn = match path {
        Some(path) => Connection::open(path)?,
        None => Connection::open_in_memory()?,
    };

    conn.execute(r#"
    CREATE TABLE IF NOT EXISTS cache (
    hash TEXT PRIMARY KEY,
    update_time TEXT,
    calendar BLOB
    );"#, ())?;

    Ok(conn)
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn cache_calendar() {
        env_logger::init();

        let db = create_cache(Some(String::from("test.db"))).unwrap();

        let cached_remote = CachedRemote {
            cache_delay: Some(10),
            remote: Remote::new("resources/test/belgium.ics"),
            cache_db: db,
        };

        debug!("Test in progress");
        cached_remote.force_cache().unwrap();

        let from_cache = cached_remote.get_from_cache().unwrap();
        let from_remote = cached_remote.remote.get().unwrap();

        assert_eq!(from_remote, from_cache);

    }
}