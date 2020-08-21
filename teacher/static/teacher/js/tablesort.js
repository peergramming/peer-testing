let ascending = true;

function sortTable(col){
	ascending = !ascending;
	const rows = Array.from(document.querySelectorAll('#myTable2 tr:not(#headers)'));
	const sorted = legSort(rows, col);
	const header = document.querySelector('#myTable2 #headers');
	sorted.forEach(row => header.insertAdjacentElement('afterend', row));
}

function compare(a, b){
	if(ascending){
		return a > b;
	} else {
		return a < b;
	}
}

function legSort(allRows, col){
	let l=[], e=[], g=[];
	const rows = Array.from(allRows);
	const pivot = rows[0].children[col].innerText;

	/* partition */
	rows.forEach(row => {
		const current = row.children[col].innerText;
		if(compare(current, pivot)){
			l.push(row);
		} else if(compare(pivot, current)) {
			g.push(row);
		} else {
			e.push(row);
		}
	});

	/* quicksort */
	if(l.length > 1){
		l = legSort(l, col);
	}
	if(g.length > 1){
		g = legSort(g, col);
	}
	return l.concat(e.concat(g));

}