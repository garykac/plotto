url = window.location.href.split("?");
if (url.length != 1 && url[1] == "random") {
	window.location.assign(url[0] + "#" + Math.floor(Math.random() * 1462 + 1));
}
