
function linkRendererTitle(link, title) {
    return '<a href="' + site_url + '/help/' + link + '" class="internal-wiki-link">' + title + '</a>';
}

function linkRenderer(link) {
    return linkRendererTitle(link, link);
}

$(document).ready(function() {
    var wikiPageName = $('#wiki-title').text();
    var wikiPageUrl = githubwiki.getGithubName(wikiPageName);

    githubwiki.setMarkedOptions({
	internalLink: linkRenderer,
	internalLinkTitle: linkRendererTitle
    });

    githubwiki.setWiki(github_repository_username, github_repository_name);

    // Sidebar
    githubwiki.get('_Sidebar.md', function(data) {
	$('#wiki-sidebar').html(data);
    });

    // Main page
    githubwiki.get(wikiPageUrl + '.md', function(data) {
	$('#wiki-content').html(data);
    });

    $('.edit-link').attr('href', 'https://github.com/' + github_repository_username + '/' + github_repository_name + '/wiki/' + wikiPageUrl + '/_edit');
});
