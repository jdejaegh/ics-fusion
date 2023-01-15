use std::{fs, io};
use std::path::{Path, PathBuf};
use url::Url;




struct Config {
    directory: Box<Path>,
}


fn list_files(directory: &Path) -> Result<Vec<PathBuf>, io::Error> {
    Ok(fs::read_dir(directory)?
        .into_iter()
        .filter(|r| r.is_ok()) // Get rid of Err variants for Result<DirEntry>
        .map(|r| r.unwrap().path()) // This is safe, since we only have the Ok variants
        .filter(|r| r.is_file()) // Filter to keep only files
        .collect())
}

fn parse_config(directory: &str) -> Result<Config, String> {
    let files = list_files(Path::new(directory))
        .expect("unable to list files in the configuration directory");

    for file in files {
        println!("{:?}", file.display());
    }

    Ok(Config { directory: Box::from(Path::new("")) })
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn parsing_config() {
        parse_config("resources/test").unwrap();
    }
}