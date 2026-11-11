/* This file is copyright (c) 2008-2013 Philippe Fournier-Viger
* 
* This file is part of the SPMF DATA MINING SOFTWARE
* (http://www.philippe-fournier-viger.com/spmf).
* 
* SPMF is free software: you can redistribute it and/or modify it under the
* terms of the GNU General Public License as published by the Free Software
* Foundation, either version 3 of the License, or (at your option) any later
* version.
* 
* SPMF is distributed in the hope that it will be useful, but WITHOUT ANY
* WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
* A PARTICULAR PURPOSE. See the GNU General Public License for more details.
* You should have received a copy of the GNU General Public License along with
* SPMF. If not, see <http://www.gnu.org/licenses/>.
*/
package ca.pfv.spmf.algorithms.frequentpatterns.phmn_plus;

import java.util.ArrayList;
import java.util.List;

/**
 * This class represents a UtilityList as used by the HUI-Miner algorithm.
 *
 * @see AlgoPHMN
 * @see ElementPHMN
 * @author Philippe Fournier-Viger
 */
public class UtilityListPHMN {
	/** the last item of the itemset this list represents */
	Integer item;
	/** the sum of the utilities of the itemset, U, negative utilities included */
	long sumIutils = 0;
	/** the sum of the remaining utilities, RU */
	long sumRutils = 0;
	/** PATCHED: the sum of the positive utilities, the PU of the corrected test PU + RU */
	long sumPutils = 0;
	/** one element per transaction that contains the itemset, in transaction order */
	List<ElementPHMN> elements = new ArrayList<ElementPHMN>();
	/** largest gap between occurrences, counting the gaps before the first and after the last */
	int largestPeriodicity = 0;
	/** smallest gap between two consecutive occurrences */
	int smallestPeriodicity = Integer.MAX_VALUE;


	/**
	 * Get the periodicity of this pattern.
	 * @return the periodicity
	 */
	public int getLargestPeriodicity() {
		return largestPeriodicity;
	}

	/**
	 * Constructor.
	 * @param item the item that is used for this utility list
	 */
	public UtilityListPHMN(Integer item){
		this.item = item;
	}
	
	/**
	 * Method to add an element to this utility list and update the sums at the same time.
	 * @param element the element of one more transaction that contains the itemset
	 */
	public void addElement(ElementPHMN element){
		sumIutils += element.iutils;
		sumRutils += element.rutils;
		sumPutils += element.putils;                          // PATCHED
		elements.add(element);
	}
	
	/**
	 * Get the support of the itemset represented by this utility-list
	 * @return the support as a number of trnsactions
	 */
	public int getSupport() {
		return elements.size();
	}
}
